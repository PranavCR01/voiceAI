"""Latency section of the streaming report (#22, first part): one table per finalization mode.

    uv run python -m harness.streaming_report --results results_stream/ \\
        --manifest data/manifests/primock57.jsonl --out reports/generated/streaming_latency.md

Reads every streaming run under `--results` (run.json + traces/), computes per-session latency
(`harness.metrics.latency`) and summarizes connection setup, time to first partial, TTFS,
finalize latency (forced mode) and endpoint delay: p50/p95 with 95% bootstrap intervals that
resample whole speakers, timeouts counted as +inf with their rate beside them, sessions per TTFS
basis, the clustering effect, and the endpoint round-trip time so geography isn't mistaken for
model speed. No ranking is printed: latency winners need the same machine, network and
>= 10 speakers (report rules in docs/DECISIONS.md), which the table states per config.
Endpointing trade-off curves (#20) and concurrency (#21) are separate sections, added with them.
"""

from __future__ import annotations

import argparse
import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from harness.datasets.manifest import read_manifest
from harness.metrics.latency import LatencySummary, SessionLatency, session_latency, summarize
from harness.metrics.stats import Interval
from harness.results import RUN_META, ResultsError, Run, read_run
from harness.streaming.trace import read_trace

METRICS = (
    ("connection_setup", "Connect"),
    ("first_partial", "First partial"),
    ("ttfs", "TTFS"),
    ("finalize_latency", "Finalize latency"),
    ("endpoint_delay", "Endpoint delay"),
)
MIN_SPEAKERS = 10


@dataclass(frozen=True)
class ConfigLatency:
    config_id: str
    mode: str  # natural | forced
    sessions: int
    speakers: int
    rtt_ms: float | None
    premature_rate: float | None  # sessions with >= 1 endpoint before the true speech end
    summaries: dict[str, LatencySummary]


def load_sessions(run: Run, run_dir: Path) -> tuple[list[SessionLatency], list[float], str]:
    sessions, rtts, modes = [], [], set()
    for row in run.rows:
        if row.error is not None or not row.raw_response_path:
            continue
        trace = read_trace(run_dir / row.raw_response_path)
        sessions.append(session_latency(trace))
        modes.add(trace.meta.finalization_mode)
        if trace.meta.rtt_ms is not None:
            rtts.append(trace.meta.rtt_ms)
    if len(modes) > 1:
        raise ValueError(f"{run.meta.run_id}: traces mix finalization modes {sorted(modes)}")
    return sessions, rtts, modes.pop() if modes else "natural"


def config_latency(
    run: Run, run_dir: Path, clusters: Mapping[str, str], *, n_resamples: int = 10_000
) -> ConfigLatency:
    sessions, rtts, mode = load_sessions(run, run_dir)
    sessions = [s for s in sessions if s.utt_id in clusters]
    summaries = {
        m: summarize(sessions, m, clusters=clusters, n_resamples=n_resamples) for m, _ in METRICS
    }
    return ConfigLatency(
        config_id=run.meta.config_id,
        mode=mode,
        sessions=len(sessions),
        speakers=len({clusters[s.utt_id] for s in sessions}),
        rtt_ms=round(statistics.median(rtts), 1) if rtts else None,
        premature_rate=(
            sum(s.premature_endpoints > 0 for s in sessions) / len(sessions) if sessions else None
        ),
        summaries=summaries,
    )


def _ms(i: Interval | None) -> str:
    if i is None:
        return "-"

    def f(x: float) -> str:
        return "timeout" if math.isinf(x) else f"{x:.0f}"

    return f"{f(i.estimate)} [{f(i.low)}, {f(i.high)}]"


def _cell(s: LatencySummary) -> str:
    if s.n == 0:
        reason = ", ".join(f"{k} {v}" for k, v in s.excluded.items()) or "no sessions"
        return f"n/a ({reason})"
    out = f"{_ms(s.p50)} / {_ms(s.p95)}"
    if s.n_timeout:
        out += f" (timeouts {100 * (s.timeout_rate or 0):.1f}%)"
    return out


def render(rows: Sequence[ConfigLatency]) -> str:
    lines = [
        "# Streaming latency",
        "",
        "Milliseconds, p50 / p95 with 95% bootstrap intervals resampling whole speakers;"
        " timeouts count as +inf (rate shown). Anchors and metric definitions:"
        " `harness/streaming/README.md`. RTT is the median TCP connect time to the endpoint."
        f" Latency is compared only between configs run from the same machine and network, and"
        f" no winner is called with fewer than {MIN_SPEAKERS} speakers.",
    ]
    for mode in ("natural", "forced"):
        group = sorted((r for r in rows if r.mode == mode), key=lambda r: r.config_id)
        if not group:
            continue
        lines += [
            "",
            f"## {'Provider endpointing' if mode == 'natural' else 'Forced finalization'} ({mode})",
            "",
            "| Config | Sessions | Speakers | RTT | "
            + " | ".join(label for _, label in METRICS)
            + " | Premature endpoints |",
            "|---|---|---|---|" + "---|" * len(METRICS) + "---|",
        ]
        for r in group:
            speakers = f"{r.speakers}" + (" (too few to call)" if r.speakers < MIN_SPEAKERS else "")
            rtt = "-" if r.rtt_ms is None else f"{r.rtt_ms:.0f}"
            premature = "-" if r.premature_rate is None else f"{100 * r.premature_rate:.1f}%"
            cells = " | ".join(_cell(r.summaries[m]) for m, _ in METRICS)
            lines.append(
                f"| {r.config_id} | {r.sessions} | {speakers} | {rtt} | {cells} | {premature} |"
            )
        notes = []
        for r in group:
            t = r.summaries["ttfs"]
            basis = ", ".join(f"{k} {v}" for k, v in t.ttfs_basis.items()) or "none"
            effect = "-" if t.cluster_effect is None else f"{t.cluster_effect:.2f}"
            notes.append(
                f"- {r.config_id}: TTFS basis {basis}; speaker clustering effect {effect}."
            )
        lines += ["", *notes]
    return "\n".join(lines) + "\n"


def streaming_runs(results_dir: Path) -> list[Run]:
    """Every streaming run under `results_dir`. A config may have a natural and a forced run
    (`stream_runner --finalization`), so uniqueness is checked per (config, mode) afterwards."""
    dirs = sorted(p.parent for p in results_dir.glob(f"*/{RUN_META}"))
    if not dirs:
        raise ResultsError(f"no runs (*/{RUN_META}) under {results_dir}")
    return [r for r in (read_run(d) for d in dirs) if r.meta.mode == "streaming"]


def check_one_run_per_config_and_mode(rows: Sequence[ConfigLatency]) -> None:
    keys = [(r.config_id, r.mode) for r in rows]
    dupes = sorted({k for k in keys if keys.count(k) > 1})
    if dupes:
        raise ResultsError(f"more than one run per (config, mode): {dupes}")


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--resamples", type=int, default=10_000)
    args = ap.parse_args(argv)
    clusters = {u.utt_id: u.speaker_id for u in read_manifest(args.manifest)}
    rows = [
        config_latency(run, args.results / run.meta.run_id, clusters, n_resamples=args.resamples)
        for run in streaming_runs(args.results)
    ]
    check_one_run_per_config_and_mode(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(rows), encoding="utf-8")
    print(f"{len(rows)} streaming runs -> {args.out}")


if __name__ == "__main__":
    main()
