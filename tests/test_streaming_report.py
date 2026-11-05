"""Latency report section (#22) on synthetic traces. Golden file: regenerate deliberately with
`UPDATE_GOLDEN=1 uv run pytest tests/test_streaming_report.py`."""

import os
from datetime import UTC, datetime
from pathlib import Path

from harness.results import ResultRow, RunMeta, read_runs, write_run
from harness.streaming.trace import (
    Event,
    EventKind,
    SessionMeta,
    SessionTrace,
    Word,
    trace_filename,
    write_trace,
)
from harness.streaming_report import config_latency, render

GOLDEN = Path(__file__).parent / "fixtures" / "streaming_latency.golden.md"
MS = 1_000_000


def trace(config: str, utt: str, mode: str, k: int, *, timeout: bool = False) -> SessionTrace:
    """Speech 0-1000 ms, 20 ms chunks sent on time after a connect of 80 + k ms."""
    setup = 80 + k
    ev = [
        Event(kind=EventKind.CONNECT_START, t_ns=0),
        Event(kind=EventKind.CONNECT_READY, t_ns=setup * MS),
    ]
    for i in range(60):  # 1,200 ms incl. trailing silence
        ev.append(
            Event(
                kind=EventKind.AUDIO_SENT,
                t_ns=(setup + 20 * i) * MS,
                chunk_index=i,
                audio_offset_ms=20.0 * i,
            )
        )
    end_sent = setup + 1000  # chunk at offset 1000 ms
    ev.append(Event(kind=EventKind.PARTIAL, t_ns=(setup + 150 + 3 * k) * MS, text="hel"))
    if mode == "forced":
        ev.append(
            Event(kind=EventKind.FINALIZE_SENT, t_ns=(end_sent + 1) * MS, audio_offset_ms=1020.0)
        )
    if not timeout:
        words = (
            Word(text="hello", start_ms=100, end_ms=500),
            Word(text="there", start_ms=600, end_ms=980),
        )
        ev.append(
            Event(
                kind=EventKind.FINAL,
                t_ns=(end_sent + 200 + 10 * k) * MS,
                text="hello there",
                words=words,
            )
        )
        if mode == "natural":
            ev.append(Event(kind=EventKind.ENDPOINT, t_ns=(end_sent + 300 + 10 * k) * MS))
    ev.append(Event(kind=EventKind.CLOSED, t_ns=(setup + 2000) * MS))
    meta = SessionMeta(
        config_id=config,
        utt_id=utt,
        chunk_ms=20,
        finalization_mode=mode,  # type: ignore[arg-type]
        speech_start_ms=0,
        speech_end_ms=1000,
        rtt_ms=20.0 + (k % 3),
    )
    return SessionTrace(meta=meta, events=tuple(sorted(ev, key=lambda e: e.t_ns)))


def build(tmp: Path) -> tuple[Path, dict[str, str]]:
    results = tmp / "results"
    clusters: dict[str, str] = {}
    for config, mode in (("prov_a_stream", "natural"), ("prov_b_stream", "forced")):
        meta = RunMeta(
            run_id=config.replace("_", "-"),
            config_id=config,
            provider="p",
            model_id="m",
            mode="streaming",
            created_at=datetime(2026, 11, 5, tzinfo=UTC),
            git_sha="abcdef0",
            manifest="m",
        )
        rows = []
        for k in range(24):
            utt = f"d:{k}"
            clusters[utt] = f"spk{k // 2}"
            name = trace_filename(utt)
            write_trace(
                results / meta.run_id / "traces" / name,
                trace(config, utt, mode, k, timeout=(config == "prov_a_stream" and k == 23)),
            )
            rows.append(
                ResultRow(utt_id=utt, hyp_text="hello there", raw_response_path=f"traces/{name}")
            )
        write_run(results, meta, rows)
    return results, clusters


def test_latency_section_golden(tmp_path: Path) -> None:
    results, clusters = build(tmp_path)
    rows = [
        config_latency(r, results / r.meta.run_id, clusters, n_resamples=200)
        for r in read_runs(results)
    ]
    out = render(rows)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.write_text(out, encoding="utf-8")
    assert out == GOLDEN.read_text(encoding="utf-8")


def test_latency_values(tmp_path: Path) -> None:
    results, clusters = build(tmp_path)
    by_id = {r.meta.config_id: r for r in read_runs(results)}
    a = config_latency(by_id["prov_a_stream"], results / "prov-a-stream", clusters, n_resamples=200)
    b = config_latency(by_id["prov_b_stream"], results / "prov-b-stream", clusters, n_resamples=200)
    assert (a.mode, b.mode, a.sessions, a.speakers) == ("natural", "forced", 24, 12)
    ttfs = a.summaries["ttfs"]
    assert ttfs.n_timeout == 1 and ttfs.ttfs_basis == {"word_timestamps": 23}
    # Natural: TTFS = 200 + 10k ms after the speech-end chunk was sent; 24 values incl. one +inf,
    # inverted-CDF p50 = 12th smallest = k=11.
    assert ttfs.p50 is not None and ttfs.p50.estimate == 310
    assert a.summaries["finalize_latency"].excluded == {"not_applicable": 24}
    assert b.summaries["endpoint_delay"].excluded == {"not_applicable": 24}
    fin = b.summaries["finalize_latency"]
    assert fin.n == 24 and fin.p50 is not None and fin.p50.estimate == 309  # 199 + 10k, k=11
    assert a.rtt_ms == 21.0 and a.premature_rate == 0.0
