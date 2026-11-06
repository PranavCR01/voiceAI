"""Audio I/O shared by every adapter, augmentation and VAD: one decoding path, so every provider
hears identical audio.

- `load_clip(utt, data_root)`: decode (ffmpeg), pick the channel, resample, then cut the
  segment in NumPy at the target rate. Whole files are decoded once and cached, so segment
  boundaries are sample-exact for every format (ffmpeg seeking is not, for MP3).
- Encoders: PCM16 little-endian, G.711 µ-law at 8 kHz (what Twilio Media Streams carry), WAV.
- `pace()`: yields fixed-size chunks at real-time pace on `time.perf_counter_ns` (monotonic and
  high-resolution on every OS; `time.monotonic` ticks every ~15.6 ms on Windows). Chunk k is
  scheduled at t0 + k * chunk, so lateness never accumulates into drift. On Windows asyncio's
  timers wake chunks up to ~15 ms late even at 1 ms timer resolution, so there the waiting
  happens in a pacing thread with `time.sleep` (a high-resolution waitable timer since Python
  3.11) until ~2 ms before each deadline, then a spin; the loop is woken by the thread, not by its
  timers (docs/DECISIONS.md, 2026-11-05/06). Timer resolution stays raised to 1 ms meanwhile.

ffmpeg is invoked as an argument list (never through a shell).
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
import subprocess
import sys
import time
import warnings
import wave
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from harness.datasets.manifest import Utterance

Int16Array = NDArray[np.int16]
Encoding = Literal["pcm16", "mulaw"]

DEFAULT_SAMPLE_RATE = 16_000
MULAW_SAMPLE_RATE = 8_000
_MULAW_SILENCE = 0xFF  # µ-law code for 0
_CACHE_FILES = 4  # decoded whole files kept in memory (manifests are sorted by file)


class AudioError(RuntimeError):
    """Decoding or probing failed."""


class SampleRateMismatchWarning(UserWarning):
    """The manifest's sample_rate disagrees with the decoded file."""


@dataclass(frozen=True)
class AudioClip:
    samples: Int16Array  # mono
    sample_rate: int
    utt_id: str
    source_sample_rate: int  # the file's own rate, as decoded

    @property
    def duration_s(self) -> float:
        return len(self.samples) / self.sample_rate


@dataclass(frozen=True)
class Chunk:
    index: int
    data: bytes
    audio_offset_ms: float  # position of the chunk start in the audio
    scheduled_ns: int  # monotonic time the chunk was due
    sent_ns: int  # monotonic time it was actually yielded

    @property
    def lateness_ms(self) -> float:
        return (self.sent_ns - self.scheduled_ns) / 1e6


# --- probing and decoding ---------------------------------------------------------------


def _run(args: list[str], stdin: bytes | None = None) -> bytes:
    try:
        proc = subprocess.run(args, input=stdin, capture_output=True, check=False)
    except OSError as e:
        raise AudioError(f"cannot run {args[0]}: {e}") from e
    if proc.returncode != 0:
        raise AudioError(f"{args[0]} failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


@dataclass(frozen=True)
class StreamInfo:
    sample_rate: int
    channels: int


def probe(path: Path) -> StreamInfo:
    if not path.is_file():
        raise FileNotFoundError(path)
    out = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "json",
            str(path),
        ]
    )
    streams = json.loads(out).get("streams") or []
    if not streams:
        raise AudioError(f"{path}: no audio stream")
    return StreamInfo(int(streams[0]["sample_rate"]), int(streams[0]["channels"]))


@lru_cache(maxsize=_CACHE_FILES)
def _decode_file(path: Path, sample_rate: int, channel: int | None) -> Int16Array:
    """Whole file as mono int16 at `sample_rate`; one channel, or a downmix when None."""
    pan = ["-af", f"pan=mono|c0=c{channel}"] if channel is not None else ["-ac", "1"]
    raw = _run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            *pan,
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-",
        ]
    )
    return np.frombuffer(raw, dtype="<i2").astype(np.int16)


def load_clip(
    utt: Utterance, data_root: Path, *, sample_rate: int = DEFAULT_SAMPLE_RATE
) -> AudioClip:
    """Decode an utterance's audio: its channel and segment, mono, at `sample_rate`."""
    path = utt.resolve_audio(data_root)
    info = probe(path)
    if utt.channel is not None and utt.channel >= info.channels:
        raise AudioError(f"{path}: channel {utt.channel} requested, file has {info.channels}")
    if info.sample_rate != utt.sample_rate:
        warnings.warn(
            f"{utt.utt_id}: manifest says {utt.sample_rate} Hz, file is {info.sample_rate} Hz",
            SampleRateMismatchWarning,
            stacklevel=2,
        )
    samples = _decode_file(path, sample_rate, utt.channel)
    if utt.start_s is not None and utt.end_s is not None:
        start = round(utt.start_s * sample_rate)
        end = min(round(utt.end_s * sample_rate), len(samples))
        if start >= len(samples):
            raise AudioError(f"{utt.utt_id}: segment starts after the end of {path}")
        samples = samples[start:end]
    return AudioClip(samples.copy(), sample_rate, utt.utt_id, info.sample_rate)


def clear_cache() -> None:
    _decode_file.cache_clear()


# --- resampling and encoders --------------------------------------------------------------


def resample(clip: AudioClip, sample_rate: int) -> AudioClip:
    if sample_rate == clip.sample_rate:
        return clip
    raw = _run(
        [
            "ffmpeg",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "s16le",
            "-ar",
            str(clip.sample_rate),
            "-ac",
            "1",
            "-i",
            "-",
            "-ar",
            str(sample_rate),
            "-f",
            "s16le",
            "-acodec",
            "pcm_s16le",
            "-",
        ],
        stdin=to_pcm16_bytes(clip),
    )
    samples = np.frombuffer(raw, dtype="<i2").astype(np.int16)
    return AudioClip(samples, sample_rate, clip.utt_id, clip.source_sample_rate)


def to_pcm16_bytes(clip: AudioClip) -> bytes:
    return clip.samples.astype("<i2").tobytes()


_MULAW_BIAS = 0x84


def mulaw_decode(data: bytes) -> Int16Array:
    code = ~np.frombuffer(data, dtype=np.uint8).astype(np.int32) & 0xFF
    sign = code & 0x80
    exponent = (code >> 4) & 0x07
    mantissa = code & 0x0F
    mag = (((mantissa << 3) + _MULAW_BIAS) << exponent) - _MULAW_BIAS
    out: Int16Array = np.where(sign != 0, -mag, mag).astype(np.int16)
    return out


def _build_mulaw_table() -> NDArray[np.uint8]:
    """ffmpeg's encoder table (libavcodec pcm_tablegen.h, build_xlaw_table): for each 14-bit
    input, the code whose decoded level is nearest, with midpoints between adjacent levels
    as thresholds. Matching it exactly keeps our encoder byte-identical to ffmpeg's pcm_mulaw,
    which the augmentation pipeline uses too."""
    mask = 0xFF
    levels = mulaw_decode(bytes(range(256))).astype(np.int32)
    table = np.zeros(16384, dtype=np.uint8)
    table[8192] = mask
    j = 1
    for i in range(127):
        v1, v2 = int(levels[i ^ mask]), int(levels[(i + 1) ^ mask])
        v = (v1 + v2 + 4) >> 3
        while j < v:
            table[8192 - j] = i ^ (mask ^ 0x80)
            table[8192 + j] = i ^ mask
            j += 1
    while j < 8192:
        table[8192 - j] = 127 ^ (mask ^ 0x80)
        table[8192 + j] = 127 ^ mask
        j += 1
    table[0] = table[1]
    return table


_MULAW_TABLE = _build_mulaw_table()


def mulaw_encode(samples: Int16Array) -> bytes:
    """G.711 µ-law, byte-identical to ffmpeg's pcm_mulaw encoder."""
    index = (samples.astype(np.int32) + 32768) >> 2
    encoded: NDArray[np.uint8] = _MULAW_TABLE[index]
    return encoded.tobytes()


def to_mulaw_8k(clip: AudioClip) -> bytes:
    return mulaw_encode(resample(clip, MULAW_SAMPLE_RATE).samples)


def to_wav_bytes(clip: AudioClip) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(clip.sample_rate)
        w.writeframes(to_pcm16_bytes(clip))
    return buf.getvalue()


# --- real-time pacing ---------------------------------------------------------------------


def encode_for_stream(clip: AudioClip, encoding: Encoding) -> tuple[bytes, int, int]:
    """(payload, bytes per second, silence byte) for streaming in `encoding`."""
    if encoding == "mulaw":
        return to_mulaw_8k(clip), MULAW_SAMPLE_RATE, _MULAW_SILENCE
    return to_pcm16_bytes(clip), clip.sample_rate * 2, 0


# Windows only: sleep until this long before a deadline, then spin on the clock. Covers the
# ~1 ms wake-up jitter left after timeBeginPeriod(1); elsewhere asyncio sleeps are precise enough.
SPIN_MARGIN_NS = 2_000_000
# Windows only: no single asyncio sleep longer than this. asyncio judges a timer due against its
# own clock plus that clock's resolution (base_events._run_once); on Python 3.12 / Windows that
# clock ticks every ~15.6 ms, so a sleep longer than one tick can be judged not yet due when its
# wait ends and is waited on again, up to a tick late. A sleep shorter than one tick always fires.
MAX_SLEEP_NS = 4_000_000
# How precise pacing waits: "thread" (time.sleep in a pacing thread; the default since the
# 2026-11-06 Windows measurements showed asyncio timers late however they are sliced) or "loop"
# (capped asyncio sleeps then a spin on the loop; kept for harness.pacing_check comparisons).
PRECISE_WAIT: Literal["thread", "loop"] = "thread"
# Windows 11 may ignore timeBeginPeriod for a throttled (e.g. background) process unless the
# process opts out via SetProcessInformation(ProcessPowerThrottling).
OPT_OUT_TIMER_THROTTLING = True
_IS_WINDOWS = sys.platform == "win32"
_PROCESS_POWER_THROTTLING = 4  # PROCESS_INFORMATION_CLASS ProcessPowerThrottling
_THROTTLING_VERSION = 1  # PROCESS_POWER_THROTTLING_CURRENT_VERSION
_IGNORE_TIMER_RESOLUTION = 0x4  # PROCESS_POWER_THROTTLING_IGNORE_TIMER_RESOLUTION


class _WinMM(Protocol):
    def timeBeginPeriod(self, period: int, /) -> int: ...  # noqa: N802 - Win32 names
    def timeEndPeriod(self, period: int, /) -> int: ...  # noqa: N802


def _load_winmm() -> _WinMM | None:
    if not _IS_WINDOWS:
        return None
    import ctypes

    try:
        winmm: Any = getattr(ctypes, "WinDLL")("winmm")  # noqa: B009 - absent off Windows
    except OSError:
        return None
    return cast(_WinMM, winmm)


class _Kernel32(Protocol):
    def GetCurrentProcess(self) -> Any: ...  # noqa: N802
    def SetProcessInformation(self, h: Any, cls: int, info: Any, size: int, /) -> int: ...  # noqa: N802


def _load_kernel32() -> _Kernel32 | None:
    if not _IS_WINDOWS:
        return None
    import ctypes

    try:
        k32: Any = getattr(ctypes, "WinDLL")("kernel32")  # noqa: B009 - absent off Windows
        k32.SetProcessInformation  # noqa: B018 - Windows 8+; probe that it exists
    except (OSError, AttributeError):
        return None
    return cast(_Kernel32, k32)


def opt_out_timer_throttling(kernel32: _Kernel32 | None) -> bool:
    """Ask Windows to always honour this process's timer-resolution request (best effort).

    Sets PROCESS_POWER_THROTTLING_STATE{version 1, control IGNORE_TIMER_RESOLUTION, state 0}:
    "never ignore the timer resolution for this process". False when unsupported (before
    Windows 11 the call fails; older Windows never throttled the resolution anyway).
    """
    if kernel32 is None:
        return False
    import ctypes

    class _State(ctypes.Structure):
        _fields_ = [  # noqa: RUF012 - ctypes declares fields as a class attribute
            ("Version", ctypes.c_uint32),
            ("ControlMask", ctypes.c_uint32),
            ("StateMask", ctypes.c_uint32),
        ]

    state = _State(_THROTTLING_VERSION, _IGNORE_TIMER_RESOLUTION, 0)
    ok = kernel32.SetProcessInformation(
        kernel32.GetCurrentProcess(),
        _PROCESS_POWER_THROTTLING,
        ctypes.byref(state),
        ctypes.sizeof(state),
    )
    return bool(ok)


@contextlib.contextmanager
def timer_resolution_1ms(winmm: _WinMM | None) -> Iterator[bool]:
    """Raise the Windows timer resolution to 1 ms for the block; yields whether it took effect.

    No-op (False) without winmm. Windows counts begin/end calls per process, so nesting is safe.
    """
    if winmm is None or winmm.timeBeginPeriod(1) != 0:  # 0 = TIMERR_NOERROR
        yield False
        return
    try:
        yield True
    finally:
        winmm.timeEndPeriod(1)


async def wait_until(
    due_ns: int,
    *,
    spin_margin_ns: int = 0,
    max_sleep_ns: int = 0,
    clock: Callable[[], int] = time.perf_counter_ns,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """Return at or after `due_ns` on `clock`.

    `spin_margin_ns` = 0: one sleep for the remaining time. > 0: sleep until that long before the
    deadline, then spin, yielding to the event loop (`sleep(0)`) so concurrent tasks (the
    receiver) keep running. An early wake-up only means a longer spin. `max_sleep_ns` > 0 splits
    the sleep into steps of at most that long (see MAX_SLEEP_NS).
    """
    if spin_margin_ns <= 0:
        remaining = due_ns - clock()
        if remaining > 0:
            await sleep(remaining / 1e9)
        return
    while (remaining := due_ns - clock() - spin_margin_ns) > 0:
        step = min(remaining, max_sleep_ns) if max_sleep_ns > 0 else remaining
        await sleep(step / 1e9)
    while clock() < due_ns:
        await sleep(0)


def block_until(
    due_ns: int,
    *,
    spin_margin_ns: int,
    clock: Callable[[], int] = time.perf_counter_ns,
    sleep: Callable[[float], object] = time.sleep,
) -> None:
    """Blocking version of `wait_until`, for the pacing thread: sleep until `spin_margin_ns`
    before the deadline (re-sleeping after an early wake-up), then spin with `sleep(0)`, which
    releases the GIL so the event loop thread (the receiver) is never starved."""
    while (remaining := due_ns - clock() - spin_margin_ns) > 0:
        sleep(remaining / 1e9)
    while clock() < due_ns:
        sleep(0)


async def pace(
    clip: AudioClip,
    *,
    chunk_ms: int = 20,
    encoding: Encoding = "pcm16",
    pad_ms: int = 0,
    precise: bool | None = None,
) -> AsyncIterator[Chunk]:
    """Yield the clip (plus `pad_ms` of trailing silence) in `chunk_ms` chunks at real time.

    Deadlines are absolute (t0 + k * chunk_ms), so a late chunk does not delay the next ones.
    `precise` (default: on Windows only) = 1 ms timer resolution (with the throttling opt-out)
    and waits per PRECISE_WAIT: in a pacing thread (`block_until`), or on the loop with sleeps of
    at most MAX_SLEEP_NS; both spin for the last SPIN_MARGIN_NS.
    """
    if chunk_ms <= 0 or pad_ms < 0:
        raise ValueError("chunk_ms must be > 0 and pad_ms >= 0")
    precise = _IS_WINDOWS if precise is None else precise
    payload, bytes_per_s, silence = encode_for_stream(clip, encoding)
    width = 2 if encoding == "pcm16" else 1
    pad_bytes = (bytes_per_s * pad_ms // 1000) // width * width
    payload += bytes([silence]) * pad_bytes
    chunk_bytes = (bytes_per_s * chunk_ms // 1000) // width * width
    chunk_ns = chunk_ms * 1_000_000
    margin = SPIN_MARGIN_NS if precise else 0
    max_sleep = MAX_SLEEP_NS if precise else 0
    if precise and OPT_OUT_TIMER_THROTTLING:
        opt_out_timer_throttling(_load_kernel32())
    pacer = (
        ThreadPoolExecutor(max_workers=1, thread_name_prefix="pace")
        if precise and PRECISE_WAIT == "thread"
        else None
    )
    loop = asyncio.get_running_loop()
    with timer_resolution_1ms(_load_winmm() if precise else None), _shutdown(pacer):
        t0 = time.perf_counter_ns()
        for k, start in enumerate(range(0, len(payload), chunk_bytes)):
            due = t0 + k * chunk_ns
            if pacer is not None:
                await loop.run_in_executor(pacer, _block, due, margin)
            else:
                await wait_until(due, spin_margin_ns=margin, max_sleep_ns=max_sleep)
            yield Chunk(
                index=k,
                data=payload[start : start + chunk_bytes],
                audio_offset_ms=k * chunk_ms,
                scheduled_ns=due,
                sent_ns=time.perf_counter_ns(),
            )


def _block(due_ns: int, margin_ns: int) -> None:
    block_until(due_ns, spin_margin_ns=margin_ns)


@contextlib.contextmanager
def _shutdown(pacer: ThreadPoolExecutor | None) -> Iterator[None]:
    try:
        yield
    finally:
        if pacer is not None:
            pacer.shutdown(wait=False)
