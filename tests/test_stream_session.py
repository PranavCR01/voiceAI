"""Streaming session against a local echo server (#18 dry-run): pacing, forced finalize timing
and trace capture, with no provider. Real time: each test streams well under a second."""

import asyncio
import json
from typing import Any

import numpy as np
import pytest
import websockets

from harness.audio import AudioClip
from harness.streaming.session import Mapped, Message, SessionError, replay, stream_session
from harness.streaming.trace import EventKind, SessionMeta

SR = 16000


class EchoProtocol:
    """Speaks to `echo_server`: binary audio in, JSON out."""

    finalize_supported = True
    encoding = "pcm16"

    def __init__(self, url: str) -> None:
        self._url = url

    def url(self) -> str:
        return self._url

    def headers(self) -> dict[str, str]:
        return {"Authorization": "Token test"}

    def audio_frame(self, data: bytes) -> Message:
        return data

    def finalize_frame(self) -> str | None:
        return json.dumps({"type": "Finalize"})

    def close_frame(self) -> str | None:
        return json.dumps({"type": "Close"})

    def handle(self, message: Message) -> list[Mapped]:
        m = json.loads(message)
        if m["type"] == "echo":
            return [Mapped(EventKind.PARTIAL, {"text": f"{m['bytes']}b"})]
        if m["type"] == "final":
            return [Mapped(EventKind.FINAL, {"text": "done"})]
        if m["type"] == "bye":
            return [Mapped(EventKind.CLOSED)]
        return []

    def is_terminal(self, message: Message) -> bool:
        return bool(json.loads(message)["type"] == "bye")


async def echo_server(ws: Any) -> None:
    async for msg in ws:
        if isinstance(msg, bytes):
            await ws.send(json.dumps({"type": "echo", "bytes": len(msg)}))
        elif json.loads(msg)["type"] == "Finalize":
            await ws.send(json.dumps({"type": "final"}))
        else:
            await ws.send(json.dumps({"type": "bye"}))
            await ws.close()
            return


def clip(seconds: float) -> AudioClip:
    return AudioClip(np.zeros(round(seconds * SR), dtype=np.int16), SR, "u:1", SR)


def meta(mode: str = "natural", speech_end_ms: float | None = None) -> SessionMeta:
    return SessionMeta(
        config_id="echo",
        utt_id="u:1",
        chunk_ms=20,
        finalization_mode=mode,  # type: ignore[arg-type]
        speech_start_ms=0,
        speech_end_ms=speech_end_ms,
    )


async def run_session(m: SessionMeta, seconds: float = 0.3, pad_ms: int = 100) -> Any:
    async with websockets.serve(echo_server, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        return await stream_session(
            EchoProtocol(f"ws://127.0.0.1:{port}"),
            clip(seconds),
            m,
            pad_ms=pad_ms,
            drain_timeout_s=2,
        )


@pytest.mark.timing
def test_natural_session_paces_every_chunk_and_records_the_echoes() -> None:
    trace = asyncio.run(run_session(meta()))
    sent = trace.of(EventKind.AUDIO_SENT)
    assert len(sent) == 20  # (300 ms audio + 100 ms silence) / 20 ms
    assert [e.audio_offset_ms for e in sent] == [20.0 * k for k in range(20)]
    # Real time: chunk k goes out ~k*20 ms after the first (allow scheduler jitter).
    span_ms = (sent[-1].t_ns - sent[0].t_ns) / 1e6
    assert 360 <= span_ms <= 520
    partials = trace.of(EventKind.PARTIAL)
    assert len(partials) == 20 and partials[0].text == "640b"  # 20 ms of 16 kHz PCM16
    assert trace.first(EventKind.FINALIZE_SENT) is None
    kinds = [e.kind for e in trace.events]
    assert kinds[0] is EventKind.CONNECT_START and kinds[1] is EventKind.CONNECT_READY
    assert kinds[-1] is EventKind.CLOSED and EventKind.AUDIO_END in kinds
    assert trace.events[-1].raw == {"type": "bye"}


def test_forced_finalize_goes_out_within_one_chunk_of_speech_end() -> None:
    trace = asyncio.run(run_session(meta("forced", speech_end_ms=150)))
    [fin] = trace.of(EventKind.FINALIZE_SENT)
    assert fin.audio_offset_ms is not None and 150 <= fin.audio_offset_ms < 150 + 20
    # It follows the audio chunk that contains 150 ms, before the next chunk is sent.
    chunk = max(
        (e for e in trace.of(EventKind.AUDIO_SENT) if e.t_ns <= fin.t_ns),
        key=lambda e: e.t_ns,
    )
    assert chunk.audio_offset_ms == 140.0
    assert fin.raw == {"type": "Finalize"}
    final = trace.first(EventKind.FINAL, after_ns=fin.t_ns)
    assert final is not None and final.text == "done"
    assert trace.text() == "done"


def test_forced_mode_needs_ground_truth_and_support() -> None:
    with pytest.raises(SessionError, match="speech_end_ms"):
        asyncio.run(run_session(meta("forced", speech_end_ms=None)))

    class NoFinalize(EchoProtocol):
        finalize_supported = False

    async def go() -> None:
        await stream_session(NoFinalize("ws://unused"), clip(0.1), meta("forced", 50))

    with pytest.raises(SessionError, match="not supported"):
        asyncio.run(go())


def test_replay_stops_at_the_terminal_message() -> None:
    p = EchoProtocol("ws://unused")
    msgs = [json.dumps({"type": t, "bytes": 4}) for t in ("echo", "final", "bye", "echo")]
    assert [m.kind for m in replay(p, msgs)] == [
        EventKind.PARTIAL,
        EventKind.FINAL,
        EventKind.CLOSED,
    ]
