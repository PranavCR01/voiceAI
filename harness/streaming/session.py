"""One streaming session, provider-independent: connect, pace the audio, optionally force a
finalize at the true speech end, record every message into a `SessionTrace`.

A provider plugs in a `StreamProtocol`: how to connect, how to frame audio and control messages,
and a *pure* `handle(message)` that maps one received message to trace events. Replay tests feed
recorded messages straight into `handle`, so the mapping is tested without a network.

Timing rules (harness/streaming/README.md):
- `audio_sent` is recorded right after the socket write returns, with the chunk's audio offset.
- Forced mode: the finalize goes out right after the chunk that contains the true speech end
  (`SessionMeta.speech_end_ms`), so it is late by at most one chunk.
- After the last audio chunk (including `pad_ms` of trailing silence) the session sends the
  provider's close message and keeps reading until the provider's terminal message, the socket
  closes, or `drain_timeout_s` passes.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from pydantic import JsonValue

from harness.audio import AudioClip, Encoding, pace
from harness.streaming.trace import EventKind, Recorder, SessionMeta, SessionTrace

Message = str | bytes


@dataclass(frozen=True)
class Mapped:
    """One trace event produced from a received message (`raw` is filled in by the session)."""

    kind: EventKind
    fields: Mapping[str, Any] = field(default_factory=dict)


class StreamProtocol(Protocol):
    finalize_supported: bool
    encoding: Encoding

    def reset(self) -> None:
        """Called at the start of every session (protocols may track per-session state)."""
        ...

    def url(self) -> str: ...

    def headers(self) -> dict[str, str]: ...

    def audio_frame(self, data: bytes) -> Message: ...

    def finalize_frame(self) -> str | None:
        """Explicit finalize / force end of turn / manual commit; None if unsupported."""
        ...

    def close_frames(self) -> list[str]:
        """Sent in order after the last audio: no more audio is coming (flush and close)."""
        ...

    def handle(self, message: Message) -> list[Mapped]:
        """Pure mapping of one received message to trace events (none for keep-alives etc.)."""
        ...

    def is_terminal(self, message: Message) -> bool:
        """True for the provider's last message of a session."""
        ...


class Socket(Protocol):
    async def send(self, message: Message) -> None: ...

    async def recv(self) -> Message: ...

    async def close(self) -> None: ...


Connect = Callable[[str, dict[str, str]], Awaitable[Socket]]


async def websockets_connect(url: str, headers: dict[str, str]) -> Socket:
    import websockets  # imported lazily so replay tests don't need a network stack

    ws = await websockets.connect(url, additional_headers=headers, max_size=None)
    return ws


def raw_of(message: Message) -> JsonValue:
    """The message as stored in the trace: parsed JSON when possible, else text/size."""
    if isinstance(message, bytes):
        return {"binary_bytes": len(message)}
    try:
        parsed: JsonValue = json.loads(message)
    except ValueError:
        return message
    return parsed


class SessionError(RuntimeError):
    pass


async def stream_session(
    protocol: StreamProtocol,
    clip: AudioClip,
    meta: SessionMeta,
    *,
    connect: Connect = websockets_connect,
    pad_ms: int = 1500,
    drain_timeout_s: float = 10.0,
    chunks: Callable[..., AsyncIterator[Any]] = pace,
) -> SessionTrace:
    if meta.finalization_mode == "forced":
        if not protocol.finalize_supported:
            raise SessionError(f"{meta.config_id}: forced finalization is not supported")
        if meta.speech_end_ms is None:
            raise SessionError(f"{meta.utt_id}: forced mode needs speech_end_ms (#15)")
    protocol.reset()
    rec = Recorder(meta)
    rec.start()
    ws = await connect(protocol.url(), protocol.headers())
    rec.record(EventKind.CONNECT_READY)
    done = asyncio.Event()

    async def receive() -> None:
        try:
            while True:
                msg = await ws.recv()
                at = time.perf_counter_ns()
                raw = raw_of(msg)
                mapped = protocol.handle(msg) or [Mapped(EventKind.INFO)]
                for m in mapped:
                    rec.record(m.kind, at_ns=at, raw=raw, **m.fields)
                if protocol.is_terminal(msg):
                    return
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 - a closed socket ends the session; record why
            rec.record(EventKind.CLOSED, raw={"reason": f"{type(e).__name__}: {e}"})
        finally:
            done.set()

    receiver = asyncio.create_task(receive())
    finalized = False
    try:
        chunk_ms = meta.chunk_ms
        async for chunk in chunks(
            clip, chunk_ms=int(chunk_ms), encoding=protocol.encoding, pad_ms=pad_ms
        ):
            if done.is_set():
                break  # provider closed early; the trace shows when
            await ws.send(protocol.audio_frame(chunk.data))
            rec.record(
                EventKind.AUDIO_SENT,
                at_ns=time.perf_counter_ns(),
                chunk_index=chunk.index,
                audio_offset_ms=chunk.audio_offset_ms,
            )
            end = chunk.audio_offset_ms + chunk_ms
            if (
                meta.finalization_mode == "forced"
                and not finalized
                and meta.speech_end_ms is not None
                and end >= meta.speech_end_ms
            ):
                frame = protocol.finalize_frame()
                assert frame is not None  # checked above via finalize_supported
                await ws.send(frame)
                rec.record(EventKind.FINALIZE_SENT, audio_offset_ms=end, raw=raw_of(frame))
                finalized = True
        rec.record(EventKind.AUDIO_END)
        for close in protocol.close_frames():
            if done.is_set():
                break
            with contextlib.suppress(Exception):
                await ws.send(close)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(done.wait(), drain_timeout_s)
    finally:
        if not receiver.done():
            receiver.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receiver
        with contextlib.suppress(Exception):
            await ws.close()
        if not any(e.kind is EventKind.CLOSED for e in rec.trace().events):
            rec.record(EventKind.CLOSED)
    return rec.trace()


def replay(protocol: StreamProtocol, messages: Sequence[Message]) -> list[Mapped]:
    """Map a recorded message sequence (a fixture) the way a live session would."""
    protocol.reset()
    out: list[Mapped] = []
    for msg in messages:
        out.extend(protocol.handle(msg) or [Mapped(EventKind.INFO)])
        if protocol.is_terminal(msg):
            break
    return out
