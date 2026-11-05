"""Streaming session traces: what every streaming adapter records, on one clock.

A trace is one (config, utterance) session: metadata plus ordered events with `t_ns`, the
high-resolution monotonic time (`time.perf_counter_ns`) since session start. Metrics
(`harness/metrics/latency.py`) are computed afterwards from traces only, so they are testable
without a live provider.

On disk (`<run>/traces/<file>.jsonl`): the first line is the metadata, each later line one event.
Schema reference: harness/streaming/README.md.
"""

from __future__ import annotations

import gzip
import time
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class EventKind(StrEnum):
    CONNECT_START = "connect_start"
    CONNECT_READY = "connect_ready"
    AUDIO_SENT = "audio_sent"
    AUDIO_END = "audio_end"
    FINALIZE_SENT = "finalize_sent"
    PARTIAL = "partial"
    FINAL = "final"
    ENDPOINT = "endpoint"
    VAD_EVENT = "vad_event"
    ERROR = "error"
    CLOSED = "closed"
    INFO = "info"  # any other provider message (session start, metadata, warnings): kept raw


FinalizationMode = Literal["natural", "forced"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Word(_Strict):
    """A recognized word with its position in the *audio* (ms from the start of the clip)."""

    text: str
    start_ms: float = Field(ge=0)
    end_ms: float = Field(ge=0)


class Event(_Strict):
    kind: EventKind
    t_ns: int = Field(ge=0)
    chunk_index: int | None = Field(default=None, ge=0)  # audio_sent
    audio_offset_ms: float | None = Field(default=None, ge=0)  # audio_sent, finalize_sent
    text: str | None = None  # partial, final
    words: tuple[Word, ...] | None = None  # final: word timings, when the provider sends them
    raw: JsonValue = None  # the provider message, for received events

    @model_validator(mode="after")
    def _fields_for_kind(self) -> Event:
        if self.kind is EventKind.AUDIO_SENT and (
            self.chunk_index is None or self.audio_offset_ms is None
        ):
            raise ValueError("audio_sent needs chunk_index and audio_offset_ms")
        if self.kind in (EventKind.PARTIAL, EventKind.FINAL) and self.text is None:
            raise ValueError(f"{self.kind} needs text")
        return self


class SessionMeta(_Strict):
    config_id: str = Field(min_length=1)
    utt_id: str = Field(min_length=1)
    chunk_ms: float = Field(gt=0)
    finalization_mode: FinalizationMode = "natural"
    finalize_supported: bool = True  # False: the provider has no explicit finalize message
    speech_start_ms: float | None = Field(default=None, ge=0)  # ground truth, audio time (#15)
    speech_end_ms: float | None = Field(default=None, ge=0)
    rtt_ms: float | None = Field(default=None, ge=0)  # network round trip probe


class SessionTrace(_Strict):
    meta: SessionMeta
    events: tuple[Event, ...]

    @model_validator(mode="after")
    def _ordered(self) -> SessionTrace:
        times = [e.t_ns for e in self.events]
        if times != sorted(times):
            raise ValueError("events must be in time order")
        offsets = [e.audio_offset_ms for e in self.events if e.kind is EventKind.AUDIO_SENT]
        if any(b <= a for a, b in zip(offsets, offsets[1:], strict=False)):  # type: ignore[operator]
            raise ValueError("audio_sent offsets must increase")
        return self

    def of(self, kind: EventKind) -> list[Event]:
        return [e for e in self.events if e.kind is kind]

    def first(self, kind: EventKind, *, after_ns: int = -1) -> Event | None:
        return next((e for e in self.events if e.kind is kind and e.t_ns > after_ns), None)

    def text(self) -> str:
        """Concatenated finals: the session's transcript for results.parquet."""
        return " ".join(e.text or "" for e in self.of(EventKind.FINAL) if e.text).strip()


def write_trace(path: Path, trace: SessionTrace) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [trace.meta.model_dump_json()] + [e.model_dump_json() for e in trace.events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


SLIM_SUFFIX = ".gz"


def slim_path(path: Path) -> Path:
    """Where the slim copy of a trace lives: `traces/<utt>.jsonl.gz` beside the full trace."""
    return path.with_name(path.name + SLIM_SUFFIX)


def write_slim_trace(path: Path, trace: SessionTrace) -> None:
    """The trace without provider payloads (`raw`), gzipped, byte-deterministic.

    Every field the metrics read (kinds, times, chunk offsets, text, word timings) is kept, so
    latency and endpointing results are identical from the slim copy; raw messages (request ids,
    ~10x the size) stay local, like batch raw responses (DECISIONS 2026-11-04).
    """
    lines = [trace.meta.model_dump_json(exclude_none=True)] + [
        e.model_copy(update={"raw": None}).model_dump_json(exclude_none=True) for e in trace.events
    ]
    data = ("\n".join(lines) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f, gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0) as gz:
        gz.write(data)


def read_trace(path: Path) -> SessionTrace:
    """Read `path`; when it is absent (a clone without raw traces), read its slim copy."""
    if not path.exists() and slim_path(path).exists():
        text = gzip.decompress(slim_path(path).read_bytes()).decode("utf-8")
    else:
        text = path.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise ValueError(f"{path}: empty trace")
    return SessionTrace(
        meta=SessionMeta.model_validate_json(lines[0]),
        events=tuple(Event.model_validate_json(ln) for ln in lines[1:]),
    )


class Recorder:
    """Builds a trace during a live session. `t_ns` is relative to `start()`.

    Pass `at_ns` (an absolute `time.perf_counter_ns()` time, e.g. a pacer chunk's `sent_ns`) to
    record when something actually happened rather than when it was logged.
    """

    def __init__(self, meta: SessionMeta) -> None:
        self.meta = meta
        self._t0: int | None = None
        self._events: list[Event] = []

    def start(self) -> None:
        self._t0 = time.perf_counter_ns()
        self.record(EventKind.CONNECT_START)

    def record(self, kind: EventKind, *, at_ns: int | None = None, **fields: object) -> Event:
        if self._t0 is None:
            raise RuntimeError("call start() first")
        now = at_ns if at_ns is not None else time.perf_counter_ns()
        event = Event.model_validate({"kind": kind, "t_ns": max(0, now - self._t0), **fields})
        self._events.append(event)
        return event

    def trace(self) -> SessionTrace:
        # Events from concurrent send/receive tasks may be appended slightly out of order.
        return SessionTrace(meta=self.meta, events=tuple(sorted(self._events, key=_t)))


def _t(e: Event) -> int:
    return e.t_ns


def trace_filename(utt_id: str) -> str:
    return utt_id.replace(":", "__").replace("/", "_") + ".jsonl"
