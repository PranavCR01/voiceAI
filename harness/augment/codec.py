"""ffmpeg round trips: resample, G.711 mu-law, Opus. Each returns the decoded samples and the exact
ffmpeg argument lists used, which the augmentation step records verbatim.

Bit-exact flags are set so the same input and ffmpeg build give the same output bytes; the ffmpeg
version is recorded beside the args because another build may not.
"""

from __future__ import annotations

import functools
import subprocess

import numpy as np

from harness.audio import AudioError, Int16Array

_BASE = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"]
_BITEXACT = ["-fflags", "+bitexact", "-flags:a", "+bitexact"]


def _pcm_in(rate: int) -> list[str]:
    return ["-f", "s16le", "-ar", str(rate), "-ac", "1", "-i", "-"]


def _pcm_out(rate: int) -> list[str]:
    return ["-ar", str(rate), "-ac", "1", "-acodec", "pcm_s16le", "-f", "s16le", "-"]


def run_ffmpeg(args: list[str], data: bytes) -> bytes:
    try:
        proc = subprocess.run(args, input=data, capture_output=True, check=False)
    except OSError as e:
        raise AudioError(f"cannot run ffmpeg: {e}") from e
    if proc.returncode != 0:
        raise AudioError(f"ffmpeg failed: {proc.stderr.decode(errors='replace').strip()}")
    return proc.stdout


@functools.cache
def ffmpeg_version() -> str:
    out = run_ffmpeg(["ffmpeg", "-hide_banner", "-version"], b"")
    return out.decode(errors="replace").splitlines()[0]


def _samples(raw: bytes) -> Int16Array:
    return np.frombuffer(raw, dtype="<i2").astype(np.int16)


def resample(samples: Int16Array, rate: int, new_rate: int) -> tuple[Int16Array, list[list[str]]]:
    args = [*_BASE, *_pcm_in(rate), *_BITEXACT, *_pcm_out(new_rate)]
    return _samples(run_ffmpeg(args, samples.astype("<i2").tobytes())), [args]


def bandpass(
    samples: Int16Array, rate: int, low_hz: float, high_hz: float, sections: int
) -> tuple[Int16Array, list[list[str]]]:
    """Telephone-channel band limit: `sections` cascaded 2-pole Butterworth high-pass filters at
    `low_hz` and as many low-pass filters at `high_hz` (12 dB/octave per section).

    The default recipe uses 2 sections (24 dB/octave), a rough stand-in for the ITU-T G.712
    300-3,400 Hz channel mask, not a reproduction of any particular network.
    """
    chain = [f"highpass=f={low_hz:g}:p=2"] * sections + [f"lowpass=f={high_hz:g}:p=2"] * sections
    args = [*_BASE, *_pcm_in(rate), *_BITEXACT, "-af", ",".join(chain), *_pcm_out(rate)]
    out = _samples(run_ffmpeg(args, samples.astype("<i2").tobytes()))
    return out[: len(samples)], [args]


def mulaw(samples: Int16Array, rate: int) -> tuple[Int16Array, list[list[str]]]:
    """Encode to G.711 mu-law and decode back, at `rate` (8 kHz for a phone line)."""
    enc = [*_BASE, *_pcm_in(rate), *_BITEXACT, "-ar", str(rate), "-acodec", "pcm_mulaw"]
    enc += ["-f", "mulaw", "-"]
    dec = [*_BASE, "-f", "mulaw", "-ar", str(rate), "-ac", "1", "-i", "-", *_BITEXACT]
    dec += _pcm_out(rate)
    encoded = run_ffmpeg(enc, samples.astype("<i2").tobytes())
    return _samples(run_ffmpeg(dec, encoded)), [enc, dec]


def opus(samples: Int16Array, rate: int, bitrate: str) -> tuple[Int16Array, list[list[str]]]:
    """Encode with libopus at `bitrate` (e.g. "12k") in Ogg, decode back to `rate`.

    The decoded length is trimmed or zero-padded to the input length: Opus adds encoder delay
    and pads the last frame, and the reference timing must not move.
    """
    enc = [*_BASE, *_pcm_in(rate), *_BITEXACT, "-c:a", "libopus", "-b:a", bitrate]
    enc += ["-serial_offset", "0", "-f", "ogg", "-"]
    dec = [*_BASE, "-f", "ogg", "-i", "-", *_BITEXACT, *_pcm_out(rate)]
    decoded = _samples(run_ffmpeg(dec, run_ffmpeg(enc, samples.astype("<i2").tobytes())))
    out = np.zeros(len(samples), dtype=np.int16)
    out[: min(len(out), len(decoded))] = decoded[: len(out)]
    return out, [enc, dec]
