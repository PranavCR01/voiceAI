"""Endpointing knob sweeps (#20): one streaming run per knob value, then a trade-off table.

    uv run python -m harness.providers.sweep run --sweep configs/sweeps/deepgram_endpointing.yaml \\
        --manifest data/manifests/primock57.jsonl --data-root data/raw --results results_sweeps/
    uv run python -m harness.providers.sweep summarize --results results_sweeps/ \\
        --manifest data/manifests/primock57.jsonl --out reports/generated/endpointing_sweep.csv

A sweep file names a streaming config, one knob and its values. Each value is a normal run
(`<config>-<knob>-<value>` run id, the value in `RunMeta.settings`, traces on disk), so every
point on the curve can be re-scored or resumed like any other run. Sweeps force
`finalization: natural`: endpointing is only measured when the provider decides. `--subset`,
`--per-speaker` and `--seed` sample the manifest as in the stream runner (same utterances for every
knob value).

The summary has one row per (config, knob value): premature and late rates with Wilson CIs and
the endpoint-delay p50/p95 with speaker-clustered CIs (`harness.metrics.endpointing`). Turn
labels come from `<manifest>.turns.jsonl` (`{"utt_id": ..., "complete": false}`) when present;
unlabelled utterances count as complete turns.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from harness.audio import AudioClip, load_clip
from harness.datasets.manifest import Utterance, read_manifest
from harness.datasets.sample import SampleSpec
from harness.env import load_env
from harness.metrics.endpointing import classify, summarize_endpoints
from harness.providers.registry import Mode, ProviderConfig, load_registry
from harness.providers.runner import RunSummary
from harness.providers.stream_runner import (
    add_sample_args,
    build_protocol,
    rtt_probe_ms,
    run_streaming,
    sample_spec,
)
from harness.results import RUN_META, Run, read_run
from harness.streaming.session import Connect, StreamProtocol, websockets_connect
from harness.streaming.trace import read_trace
from harness.vad import SpeechSpan, read_speech, sidecar_path


class Sweep(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    config: str = Field(min_length=1)
    knob: str = Field(pattern=r"^[a-z_]+$")
    values: list[JsonValue] = Field(min_length=1)
    notes: str = ""


def load_sweep(path: Path) -> Sweep:
    return Sweep.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _slug(value: JsonValue) -> str:
    return str(value).lower().replace(".", "p").replace("-", "m")


def sweep_points(base: ProviderConfig, sweep: Sweep) -> list[tuple[str, ProviderConfig]]:
    """(run id, config with the knob set and natural finalization) per value."""
    if base.mode is not Mode.STREAMING:
        raise ValueError(f"{base.config_id} is not a streaming config")
    if len({json.dumps(v) for v in sweep.values}) != len(sweep.values):
        raise ValueError("duplicate sweep values")
    points = []
    for value in sweep.values:
        settings = {**base.settings, sweep.knob: value, "finalization": "natural"}
        run_id = f"{base.config_id}-{sweep.knob}-{_slug(value)}".replace("_", "-")
        points.append((run_id, base.model_copy(update={"settings": settings})))
    return points


async def run_sweep(
    base: ProviderConfig,
    sweep: Sweep,
    manifest: Sequence[Utterance],
    *,
    build: Callable[[ProviderConfig], StreamProtocol],
    load: Callable[[Utterance], AudioClip],
    spans: Mapping[str, SpeechSpan],
    results_dir: Path,
    manifest_label: str,
    connect: Connect = websockets_connect,
    limit: int | None = None,
    sha: str | None = None,
    rtt_ms: float | None = None,
    sample: SampleSpec | None = None,
    max_sessions_per_minute: int | None = None,
) -> list[RunSummary]:
    summaries = []
    for run_id, cfg in sweep_points(base, sweep):
        summaries.append(
            await run_streaming(
                cfg,
                build(cfg),
                manifest,
                load=load,
                spans=spans,
                results_dir=results_dir,
                manifest_label=manifest_label,
                run_id=run_id,
                limit=limit,
                connect=connect,
                sha=sha,
                rtt_ms=rtt_ms,
                sample=sample,
                max_sessions_per_minute=max_sessions_per_minute,
            )
        )
    return summaries


FIELDS = [
    "config_id", "run_id", "knob", "value", "sessions", "unscorable",
    "premature_rate", "premature_low", "premature_high",
    "late_rate", "late_low", "late_high",
    "delay_p50_ms", "delay_p50_low", "delay_p50_high",
    "delay_p95_ms", "delay_p95_low", "delay_p95_high",
]  # fmt: skip


def summarize_runs(
    results_dir: Path,
    clusters: Mapping[str, str],
    complete: Mapping[str, bool],
    *,
    knob_of: Mapping[str, str] | None = None,
    n_resamples: int = 10_000,
) -> list[dict[str, JsonValue]]:
    """One row per streaming run whose settings name a swept knob (`knob_of`: run id -> knob;
    by default, the single setting that differs from the other runs of the same config)."""
    runs = [r for r in sweep_runs(results_dir) if r.meta.mode == "streaming"]
    knob_of = dict(knob_of or _infer_knobs(runs))
    rows: list[dict[str, JsonValue]] = []
    for run in sorted(runs, key=lambda r: (r.meta.config_id, r.meta.run_id)):
        knob = knob_of.get(run.meta.run_id)
        if knob is None:
            continue
        outcomes = [
            classify(
                read_trace(results_dir / run.meta.run_id / row.raw_response_path),
                complete=complete.get(row.utt_id, True),
            )
            for row in run.rows
            if row.error is None and row.raw_response_path and row.utt_id in clusters
        ]
        s = summarize_endpoints(outcomes, clusters=clusters, n_resamples=n_resamples)

        def iv(i: object, scale: float = 1.0) -> list[JsonValue]:
            if i is None:
                return [None, None, None]
            return [round(getattr(i, k) * scale, 4) for k in ("estimate", "low", "high")]

        rows.append(
            dict(
                zip(
                    FIELDS,
                    [
                        run.meta.config_id,
                        run.meta.run_id,
                        knob,
                        run.meta.settings.get(knob),
                        s.sessions,
                        s.unscorable,
                        *iv(s.premature),
                        *iv(s.late),
                        *iv(s.delay_p50),
                        *iv(s.delay_p95),
                    ],
                    strict=True,
                )
            )
        )
    return rows


def sweep_runs(results_dir: Path) -> list[Run]:
    """Every run under `results_dir`. Unlike `read_runs`, several runs of one config are expected:
    a sweep is one config at many knob values."""
    return [read_run(d) for d in sorted(results_dir.iterdir()) if (d / RUN_META).exists()]


def _infer_knobs(runs: Sequence[Run]) -> dict[str, str]:
    by_config: dict[str, list[Run]] = {}
    for r in runs:
        by_config.setdefault(r.meta.config_id, []).append(r)
    out: dict[str, str] = {}
    for group in by_config.values():
        if len(group) < 2:
            continue
        keys = set().union(*(r.meta.settings for r in group))
        varying = [k for k in keys if len({json.dumps(r.meta.settings.get(k)) for r in group}) > 1]
        if len(varying) == 1:
            out.update({r.meta.run_id: varying[0] for r in group})
    return out


def write_csv(path: Path, rows: Sequence[Mapping[str, JsonValue]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def turn_labels(manifest: Path) -> dict[str, bool]:
    path = manifest.with_name(manifest.name.removesuffix(".jsonl") + ".turns.jsonl")
    if not path.exists():
        return {}
    labels = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            labels[str(rec["utt_id"])] = bool(rec["complete"])
    return labels


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--sweep", type=Path, required=True)
    r.add_argument("--manifest", type=Path, required=True)
    r.add_argument("--data-root", type=Path, required=True)
    r.add_argument("--results", type=Path, required=True)
    r.add_argument("--registry", type=Path, default=Path("configs/providers.yaml"))
    r.add_argument("--limit", type=int)
    add_sample_args(r)
    r.add_argument("--max-sessions-per-minute", type=int, help="see stream_runner")
    s = sub.add_parser("summarize")
    s.add_argument("--results", type=Path, required=True)
    s.add_argument("--manifest", type=Path, required=True)
    s.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)

    if args.cmd == "summarize":
        utts = read_manifest(args.manifest)
        rows = summarize_runs(
            args.results, {u.utt_id: u.speaker_id for u in utts}, turn_labels(args.manifest)
        )
        write_csv(args.out, rows)
        print(f"{len(rows)} sweep points -> {args.out}")
        return

    sweep = load_sweep(args.sweep)
    base = load_registry(args.registry).get(sweep.config)
    load_env()
    api_key = os.environ.get(base.env_key, "")
    if not api_key:
        raise SystemExit(f"{base.env_key} is not set")
    side = sidecar_path(args.manifest)
    data_root: Path = args.data_root
    protocol = build_protocol(base, api_key, None)
    summaries = asyncio.run(
        run_sweep(
            base,
            sweep,
            read_manifest(args.manifest),
            build=lambda cfg: build_protocol(cfg, api_key, None),
            load=lambda u: load_clip(u, data_root),
            spans=read_speech(side) if side.exists() else {},
            results_dir=args.results,
            manifest_label=str(args.manifest),
            limit=args.limit,
            rtt_ms=rtt_probe_ms(protocol.url()),
            sample=sample_spec(args),
            max_sessions_per_minute=args.max_sessions_per_minute,
        )
    )
    for summ in summaries:
        print(f"{summ.run_dir}: {summ.succeeded} ok, {summ.failed} failed")


if __name__ == "__main__":
    main()
