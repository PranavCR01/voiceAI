"""Streaming runs (#18): one session per utterance, one at a time, traces on disk.

    uv run python -m harness.providers.stream_runner --config deepgram_nova3_stream \\
        --manifest data/manifests/primock57.jsonl --data-root data/raw --results results_stream/

Sessions run sequentially: overlapping sessions on one machine would compete for CPU and network
and distort latency; concurrency is its own measurement (#21). Per utterance the run writes
`traces/<utt>.jsonl` (harness/streaming/README.md) and a `results.parquet` row whose `hyp_text`
is the concatenated finals, so the offline report scores streaming WER unchanged. Resumes like
the batch runner. Latency numbers are only meaningful from one fixed machine and network (the
owner's); a cloud session is fine for checking protocols and capturing fixtures.

Session settings live in the registry entry next to the provider's own settings and are removed
before the adapter sees them: `chunk_ms` (20), `finalization` (`natural` | `forced`),
`trailing_silence_ms` (1500), `encoding` (`pcm16` | `mulaw`).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
import statistics
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from pydantic import JsonValue

from harness.audio import AudioClip, Encoding, load_clip
from harness.datasets.manifest import Utterance, read_manifest
from harness.metrics.wer import empty_on_speech
from harness.providers.registry import Mode, ProviderConfig, load_registry
from harness.providers.runner import (
    RunSummary,
    _check_resumable,
    _meta_for,
    git_sha,
    profile_keyterms,
)
from harness.results import RUN_META, ResultRow, read_run, write_run
from harness.streaming.session import Connect, StreamProtocol, stream_session, websockets_connect
from harness.streaming.trace import FinalizationMode, SessionMeta, trace_filename, write_trace
from harness.vad import SpeechSpan, read_speech, sidecar_path
from recommender.profile import load_profile

SESSION_DEFAULTS: dict[str, JsonValue] = {
    "chunk_ms": 20,
    "finalization": "natural",
    "trailing_silence_ms": 1500,
    "encoding": "pcm16",
}

# (config, api key, provider settings, keyterms, encoding) -> protocol
ProtocolFactory = Callable[
    [ProviderConfig, str, Mapping[str, JsonValue], list[str] | None, Encoding], StreamProtocol
]


def stream_adapters() -> dict[str, ProtocolFactory]:
    from harness.providers.assemblyai_stream import AssemblyAIStream
    from harness.providers.deepgram_stream import DeepgramStream
    from harness.providers.elevenlabs_stream import ElevenLabsStream

    return {
        "deepgram": DeepgramStream,
        "assemblyai": AssemblyAIStream,
        "elevenlabs": ElevenLabsStream,
    }


@dataclass(frozen=True)
class SessionSettings:
    chunk_ms: int
    finalization: FinalizationMode
    trailing_silence_ms: int
    encoding: Encoding


def split_settings(
    settings: Mapping[str, JsonValue],
) -> tuple[SessionSettings, dict[str, JsonValue]]:
    merged = {**SESSION_DEFAULTS, **{k: v for k, v in settings.items() if k in SESSION_DEFAULTS}}
    provider = {k: v for k, v in settings.items() if k not in SESSION_DEFAULTS}
    s = SessionSettings(
        chunk_ms=int(cast(int, merged["chunk_ms"])),
        finalization=cast(FinalizationMode, merged["finalization"]),
        trailing_silence_ms=int(cast(int, merged["trailing_silence_ms"])),
        encoding=cast(Encoding, merged["encoding"]),
    )
    if s.finalization not in ("natural", "forced"):
        raise ValueError(f"finalization must be natural or forced, not {s.finalization!r}")
    if s.encoding not in ("pcm16", "mulaw"):
        raise ValueError(f"encoding must be pcm16 or mulaw, not {s.encoding!r}")
    if s.chunk_ms <= 0 or s.trailing_silence_ms < 0:
        raise ValueError("chunk_ms must be > 0 and trailing_silence_ms >= 0")
    return s, provider


def rtt_probe_ms(url: str, attempts: int = 5, timeout_s: float = 5.0) -> float | None:
    """Median TCP connect time to the endpoint's host: network distance, not model speed.

    Through an HTTP proxy this measures the hop to the proxy, so it is only meaningful on a
    direct connection (the owner's machine); None when the host can't be reached.
    """
    parts = urlsplit(url)
    host = parts.hostname
    if host is None:
        return None
    port = parts.port or (443 if parts.scheme in ("wss", "https") else 80)
    samples = []
    for _ in range(attempts):
        t0 = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout_s):
                samples.append((time.perf_counter() - t0) * 1000)
        except OSError:
            return None
    return round(statistics.median(samples), 2)


def session_meta(
    config_id: str, utt: Utterance, s: SessionSettings, span: SpeechSpan | None, rtt: float | None
) -> SessionMeta:
    return SessionMeta(
        config_id=config_id,
        utt_id=utt.utt_id,
        chunk_ms=s.chunk_ms,
        finalization_mode=s.finalization,
        speech_start_ms=span.speech_start_ms if span else None,
        speech_end_ms=span.speech_end_ms if span else None,
        rtt_ms=rtt,
    )


async def run_streaming(
    config: ProviderConfig,
    protocol: StreamProtocol,
    manifest: Sequence[Utterance],
    *,
    load: Callable[[Utterance], AudioClip],
    spans: Mapping[str, SpeechSpan],
    results_dir: Path,
    manifest_label: str,
    run_id: str | None = None,
    limit: int | None = None,
    include_excluded: bool = False,
    retry_failed: bool = False,
    flush_every: int = 10,
    connect: Connect = websockets_connect,
    sha: str | None = None,
    keyterms: list[str] | None = None,
    rtt_ms: float | None = None,
) -> RunSummary:
    if config.mode is not Mode.STREAMING:
        raise ValueError(f"{config.config_id} is a {config.mode} config; use the batch runner")
    s, _ = split_settings(config.settings)
    if s.finalization == "forced" and not protocol.finalize_supported:
        raise ValueError(f"{config.config_id}: the provider has no explicit finalize")
    run_id = run_id or config.config_id.replace("_", "-")
    run_dir = results_dir / run_id
    rows: dict[str, ResultRow] = {}
    if (run_dir / RUN_META).exists():
        existing = read_run(run_dir)
        _check_resumable(existing.meta, config, keyterms)
        meta = existing.meta
        rows = {r.utt_id: r for r in existing.rows if not (retry_failed and r.error is not None)}
    else:
        meta = _meta_for(config, run_id, manifest_label, sha or git_sha(), keyterms)
    skipped_excluded = (
        0 if include_excluded else sum(u.exclude_reason is not None for u in manifest)
    )
    candidates = [u for u in manifest if include_excluded or u.exclude_reason is None]
    candidates = candidates[:limit] if limit is not None else candidates
    todo = [u for u in candidates if u.utt_id not in rows]
    (run_dir / "traces").mkdir(parents=True, exist_ok=True)
    write_run(results_dir, meta, rows.values())

    done: list[ResultRow] = []
    for n, utt in enumerate(todo, 1):
        started = datetime.now(UTC)
        span = spans.get(utt.utt_id)
        try:
            if s.finalization == "forced" and (span is None or span.speech_end_ms is None):
                raise ValueError("no VAD speech end (#15) for forced finalization")
            trace = await stream_session(
                protocol,
                await asyncio.to_thread(load, utt),
                session_meta(config.config_id, utt, s, span, rtt_ms),
                connect=connect,
                pad_ms=s.trailing_silence_ms,
            )
        except Exception as e:  # noqa: BLE001 - recorded per utterance, the run goes on
            row = ResultRow(
                utt_id=utt.utt_id,
                hyp_text="",
                started_at=started,
                finished_at=datetime.now(UTC),
                error=f"{type(e).__name__}: {e}",
            )
        else:
            name = trace_filename(utt.utt_id)
            write_trace(run_dir / "traces" / name, trace)
            text = trace.text()
            row = ResultRow(
                utt_id=utt.utt_id,
                hyp_text=text,
                raw_response_path=f"traces/{name}",
                started_at=started,
                finished_at=datetime.now(UTC),
                suspect_empty=empty_on_speech(utt.ref_text, text),
            )
        rows[utt.utt_id] = row
        done.append(row)
        if n % flush_every == 0:
            write_run(results_dir, meta, rows.values())
    write_run(results_dir, meta, rows.values())
    return RunSummary(
        run_dir=run_dir,
        attempted=len(todo),
        succeeded=sum(r.error is None for r in done),
        failed=sum(r.error is not None for r in done),
        skipped_existing=len(candidates) - len(todo),
        skipped_excluded=skipped_excluded,
        suspect_empty=sum(r.suspect_empty for r in done),
    )


def build_protocol(
    config: ProviderConfig, api_key: str, keyterms: list[str] | None
) -> StreamProtocol:
    adapters = stream_adapters()
    if config.provider not in adapters:
        raise ValueError(f"no streaming adapter for provider {config.provider!r}")
    s, provider_settings = split_settings(config.settings)
    return adapters[config.provider](config, api_key, provider_settings, keyterms, s.encoding)


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--data-root", type=Path, required=True)
    ap.add_argument("--results", type=Path, required=True)
    ap.add_argument("--registry", type=Path, default=Path("configs/providers.yaml"))
    ap.add_argument("--run-id")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--include-excluded", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--profile", type=Path, help="for keyterms: profile / lexicon")
    ap.add_argument("--no-rtt", action="store_true", help="skip the network round-trip probe")
    args = ap.parse_args(argv)

    config = load_registry(args.registry).get(args.config)
    if config.verify:
        print(f"warning: {config.config_id} has unverified model id/pricing (verify: true)")
    api_key = os.environ.get(config.env_key, "")
    if not api_key:
        raise SystemExit(f"{config.env_key} is not set")
    keyterms = profile_keyterms(config, load_profile(args.profile)) if args.profile else None
    protocol = build_protocol(config, api_key, keyterms)
    side = sidecar_path(args.manifest)
    spans = read_speech(side) if side.exists() else {}
    data_root: Path = args.data_root

    def load(u: Utterance) -> AudioClip:
        return load_clip(u, data_root)

    summary = asyncio.run(
        run_streaming(
            config,
            protocol,
            read_manifest(args.manifest),
            load=load,
            spans=spans,
            results_dir=args.results,
            manifest_label=str(args.manifest),
            run_id=args.run_id,
            limit=args.limit,
            include_excluded=args.include_excluded,
            retry_failed=args.retry_failed,
            keyterms=keyterms,
            rtt_ms=None if args.no_rtt else rtt_probe_ms(protocol.url()),
        )
    )
    print(
        f"{summary.run_dir}: {summary.succeeded} ok, {summary.failed} failed, "
        f"{summary.skipped_existing} already done, {summary.skipped_excluded} excluded, "
        f"{summary.suspect_empty} empty on speech"
    )


if __name__ == "__main__":
    main()
