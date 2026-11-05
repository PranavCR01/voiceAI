"""Additive noise at a target SNR, measured on the speech region.

SNR = 10·log10(P_speech / P_noise), both powers taken over the same sample range: the speech
region (VAD bounds, #15) when known, else the whole clip. Measuring over the whole clip would
count leading/trailing silence as "speech" and make the effective SNR worse than labelled.
If the mix would clip, the whole mix is scaled down, which keeps the SNR; the scale is recorded.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from harness.audio import Int16Array

_FULL_SCALE = 32767.0


class SilentRegionError(ValueError):
    """The speech region has no energy, so an SNR is undefined."""


@dataclass(frozen=True)
class Region:
    start: int  # sample index, inclusive
    end: int  # sample index, exclusive
    basis: str  # "vad" or "whole_clip"


def power(x: NDArray[np.floating] | Int16Array) -> float:
    xf = np.asarray(x, dtype=np.float64)
    return float(np.mean(xf * xf)) if len(xf) else 0.0


def snr_db(speech: Int16Array | NDArray[np.floating], noise: NDArray[np.floating]) -> float:
    return float(10.0 * np.log10(power(speech) / power(noise)))


def pick_segment(
    noise: Int16Array, length: int, rng: np.random.Generator
) -> tuple[Int16Array, int]:
    """A `length`-sample segment at a seeded offset; a noise file shorter than that is tiled."""
    if len(noise) == 0:
        raise ValueError("empty noise file")
    if len(noise) < length:
        reps = -(-length // len(noise))
        return np.tile(noise, reps)[:length], 0
    offset = int(rng.integers(0, len(noise) - length + 1))
    return noise[offset : offset + length], offset


@dataclass(frozen=True)
class Mixed:
    samples: Int16Array
    noise_gain: float  # applied to the noise segment before mixing
    peak_scale: float  # applied to the whole mix to avoid clipping (1.0 = none)


def mix(speech: Int16Array, noise: Int16Array, target_snr_db: float, region: Region) -> Mixed:
    """Mix equal-length `noise` into `speech` so the SNR over `region` is `target_snr_db`."""
    if len(noise) != len(speech):
        raise ValueError("noise segment and speech differ in length")
    s = speech.astype(np.float64)
    n = noise.astype(np.float64)
    p_s, p_n = power(s[region.start : region.end]), power(n[region.start : region.end])
    if p_s == 0.0:
        raise SilentRegionError("speech region is silent")
    if p_n == 0.0:
        raise ValueError("noise segment is silent over the speech region")
    gain = float(np.sqrt(p_s / (p_n * 10.0 ** (target_snr_db / 10.0))))
    out = s + gain * n
    peak = float(np.max(np.abs(out)))
    scale = min(1.0, _FULL_SCALE / peak) if peak > 0 else 1.0
    samples = np.round(out * scale).clip(-32768, 32767).astype(np.int16)
    return Mixed(samples, gain, scale)
