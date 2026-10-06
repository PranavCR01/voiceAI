"""Audio I/O shared by every adapter, augmentation and VAD: one decoding path, so every provider
hears identical audio.

- `load_clip(utt, data_root)`: decode (ffmpeg), pick the channel, resample, then cut the
  segment in NumPy at the target rate. Whole files are decoded once and cached, so segment
  boundaries are sample-exact for every format (ffmpeg seeking is not, for MP3).
- Encoders: PCM16 little-endian, G.711 µ-law at 8 kHz (what Twilio Media Streams carry), WAV.
- `pace()`: yields fixed-size chunks at real-time pace on the monotonic clock. Chunk k is
  scheduled at t0 + k * chunk, so lateness never accumulates into drift.

ffmpeg is invoked as an argument list (never through a shell).
"""

from __future__ import annotations

import asyncio
import io
import json
import subprocess
import time
import warnings
import wave
from collections.abc import AsyncIterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

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


async def pace(
    clip: AudioClip,
    *,
    chunk_ms: int = 20,
    encoding: Encoding = "pcm16",
    pad_ms: int = 0,
) -> AsyncIterator[Chunk]:
    """Yield the clip (plus `pad_ms` of trailing silence) in `chunk_ms` chunks at real time.

    Deadlines are absolute (t0 + k * chunk_ms), so a late chunk does not delay the next ones.
    """
    if chunk_ms <= 0 or pad_ms < 0:
        raise ValueError("chunk_ms must be > 0 and pad_ms >= 0")
    payload, bytes_per_s, silence = encode_for_stream(clip, encoding)
    width = 2 if encoding == "pcm16" else 1
    pad_bytes = (bytes_per_s * pad_ms // 1000) // width * width
    payload += bytes([silence]) * pad_bytes
    chunk_bytes = (bytes_per_s * chunk_ms // 1000) // width * width
    chunk_ns = chunk_ms * 1_000_000
    t0 = time.monotonic_ns()
    for k, start in enumerate(range(0, len(payload), chunk_bytes)):
        due = t0 + k * chunk_ns
        wait = due - time.monotonic_ns()
        if wait > 0:
            await asyncio.sleep(wait / 1e9)
        yield Chunk(
            index=k,
            data=payload[start : start + chunk_bytes],
            audio_offset_ms=k * chunk_ms,
            scheduled_ns=due,
            sent_ns=time.monotonic_ns(),
        )
