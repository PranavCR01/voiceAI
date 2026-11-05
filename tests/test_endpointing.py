"""Endpointing outcomes (#20) on hand-written traces, and sweep orchestration on the echo server."""

import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import websockets

from harness.audio import AudioClip
from harness.datasets.manifest import Utterance
from harness.metrics.endpointing import classify, summarize_endpoints
from harness.providers.registry import ProviderConfig
from harness.providers.sweep import (
    Sweep,
    load_sweep,
    run_sweep,
    summarize_runs,
    sweep_points,
    sweep_runs,
    write_csv,
)
from harness.streaming.session import Mapped, Message
from harness.streaming.trace import Event, EventKind, SessionMeta, SessionTrace

ROOT = Path(__file__).resolve().parent.parent
MS = 1_000_000


def trace(
    endpoints_ms: list[int], *, mode: str = "natural", speech_end: float | None = 1000
) -> SessionTrace:
    """Chunk k (20 ms of audio) sent at t = 20k ms; speech ends at 1000 ms of audio = t 1000 ms."""
    ev = [Event(kind=EventKind.CONNECT_START, t_ns=0), Event(kind=EventKind.CONNECT_READY, t_ns=0)]
    ev += [
        Event(kind=EventKind.AUDIO_SENT, t_ns=20 * k * MS, chunk_index=k, audio_offset_ms=20.0 * k)
        for k in range(100)
    ]
    ev += [Event(kind=EventKind.ENDPOINT, t_ns=t * MS) for t in endpoints_ms]
    meta = SessionMeta(
        config_id="c",
        utt_id="u:1",
        chunk_ms=20,
        finalization_mode=mode,  # type: ignore[arg-type]
        speech_start_ms=0,
        speech_end_ms=speech_end,
    )
    return SessionTrace(meta=meta, events=tuple(sorted(ev, key=lambda e: e.t_ns)))


def test_correct_endpoint_has_its_delay() -> None:
    o = classify(trace([1450]))
    assert (o.outcome, o.delay_ms) == ("correct", 450)


def test_endpoint_during_a_mid_sentence_pause_is_premature() -> None:
    # "my number is ... 07700": the provider fired at 600 ms, in the pause, then at the end.
    o = classify(trace([600, 1300]))
    assert (o.outcome, o.premature_count, o.delay_ms) == ("premature", 1, None)


def test_late_and_missing_endpoints() -> None:
    assert classify(trace([4500])).outcome == "late"  # 3.5 s after the end > 3 s
    assert classify(trace([4500]), late_after_ms=4000).outcome == "correct"
    assert classify(trace([])).outcome == "late"


def test_incomplete_turns_must_not_be_endpointed() -> None:
    assert classify(trace([1800]), complete=False).outcome == "premature"
    assert classify(trace([]), complete=False).outcome == "correct"


def test_unscorable_sessions() -> None:
    assert classify(trace([1200], mode="forced")).outcome == "unscorable"
    assert classify(trace([1200], speech_end=None)).outcome == "unscorable"


def test_summary_rates_and_delays() -> None:
    outs = [classify(trace([1000 + 100 * k])) for k in range(8)] + [
        classify(trace([500])),
        classify(trace([])),
    ]
    outs += [classify(trace([1200], mode="forced"))]
    s = summarize_endpoints(outs, n_resamples=200)
    assert (s.sessions, s.unscorable, s.counts["correct"]) == (10, 1, 8)
    assert s.premature is not None and s.premature.estimate == pytest.approx(0.1)
    assert s.late is not None and s.late.estimate == pytest.approx(0.1)
    assert s.delay_p50 is not None and s.delay_p50.estimate == 300  # inverted-CDF p50 of 0..700


# --- sweep orchestration ------------------------------------------------------------------------


class EndpointEcho:
    """Echo-server protocol that reports an endpoint for every chunk after 120 ms of audio."""

    finalize_supported = True
    encoding = "pcm16"

    def __init__(self, url: str) -> None:
        self._url, self.n = url, 0

    def reset(self) -> None:
        self.n = 0

    def url(self) -> str:
        return self._url

    def headers(self) -> dict[str, str]:
        return {}

    def audio_frame(self, data: bytes) -> Message:
        return data

    def finalize_frame(self) -> str | None:
        return None

    def close_frames(self) -> list[str]:
        return [json.dumps({"type": "Close"})]

    def handle(self, message: Message) -> list[Mapped]:
        m = json.loads(message)
        if m["type"] == "echo":
            self.n += 1
            return (
                [Mapped(EventKind.ENDPOINT)]
                if self.n == 8
                else [Mapped(EventKind.PARTIAL, {"text": "x"})]
            )
        return []

    def is_terminal(self, message: Message) -> bool:
        return bool(json.loads(message)["type"] == "bye")


async def echo(ws: Any) -> None:
    async for msg in ws:
        if isinstance(msg, bytes):
            await ws.send(json.dumps({"type": "echo"}))
        else:
            await ws.send(json.dumps({"type": "bye"}))
            await ws.close()
            return


def base_config() -> ProviderConfig:
    return ProviderConfig.model_validate(
        {
            "config_id": "echo_stream",
            "provider": "echo",
            "model_id": "m",
            "mode": "streaming",
            "settings": {"trailing_silence_ms": 40, "finalization": "forced"},
            "env_key": "X",
            "pricing": {
                "amount": 1,
                "unit": "hour",
                "billing_basis": "audio_duration",
                "source": "t",
                "as_of": "2026-11-05",
            },
        }
    )


def test_each_knob_value_is_a_run_with_the_value_in_its_settings(tmp_path: Path) -> None:
    from harness.vad import SpeechSpan

    sweep = Sweep(config="echo_stream", knob="endpointing", values=[100, 300])
    utts = [
        Utterance(
            utt_id=f"d:{i}",
            dataset="d",
            subset="s",
            speaker_id=f"spk{i}",
            audio_path="a.wav",
            ref_text="x",
            sample_rate=16000,
            license="CC0-1.0",
        )
        for i in range(2)
    ]
    spans = {
        u.utt_id: SpeechSpan(
            utt_id=u.utt_id,
            speech_start_ms=0,
            speech_end_ms=100,
            clip_ms=160,
            coverage=0.6,
            vad_id="t",
        )
        for u in utts
    }

    async def go() -> Any:
        async with websockets.serve(echo, "127.0.0.1", 0) as server:
            url = f"ws://127.0.0.1:{server.sockets[0].getsockname()[1]}"
            return await run_sweep(
                base_config(),
                sweep,
                utts,
                build=lambda cfg: EndpointEcho(url),
                load=lambda u: AudioClip(np.zeros(2560, dtype=np.int16), 16000, u.utt_id, 16000),
                spans=spans,
                results_dir=tmp_path,
                manifest_label="t",
                sha="abcdef0",
            )

    summaries = asyncio.run(go())
    assert [(s.succeeded, s.failed) for s in summaries] == [(2, 0), (2, 0)]
    runs = {r.meta.run_id: r.meta.settings for r in sweep_runs(tmp_path)}
    assert runs == {
        "echo-stream-endpointing-100": {
            "trailing_silence_ms": 40,
            "finalization": "natural",
            "endpointing": 100,
        },
        "echo-stream-endpointing-300": {
            "trailing_silence_ms": 40,
            "finalization": "natural",
            "endpointing": 300,
        },
    }
    rows = summarize_runs(tmp_path, {u.utt_id: u.speaker_id for u in utts}, {}, n_resamples=100)
    assert [(r["value"], r["sessions"]) for r in rows] == [(100, 2), (300, 2)]
    # The 8th chunk (offset 140 ms) is sent after the 100 ms speech end: correct, ~40 ms delay.
    assert all(r["premature_rate"] == 0 and r["late_rate"] == 0 for r in rows)
    write_csv(tmp_path / "sweep.csv", rows)
    assert (
        (tmp_path / "sweep.csv")
        .read_text()
        .splitlines()[0]
        .startswith("config_id,run_id,knob,value")
    )


def test_sweep_points_and_committed_sweeps() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        sweep_points(base_config(), Sweep(config="echo_stream", knob="endpointing", values=[1, 1]))
    [(run_id, cfg)] = sweep_points(
        base_config(), Sweep(config="echo_stream", knob="eot_threshold", values=[0.7])
    )
    assert run_id == "echo-stream-eot-threshold-0p7" and cfg.settings["eot_threshold"] == 0.7
    from harness.providers.registry import load_registry
    from harness.providers.stream_runner import build_protocol

    reg = load_registry(ROOT / "configs" / "providers.yaml")
    for path in sorted((ROOT / "configs" / "sweeps").glob("*.yaml")):
        sweep = load_sweep(path)
        for _, cfg in sweep_points(reg.get(sweep.config), sweep):
            build_protocol(cfg, "K", None)  # every knob is a setting the adapter accepts
