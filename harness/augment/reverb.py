"""Room reverberation: convolve with a room impulse response (RIR).

The output is aligned on the RIR's direct-path peak (its largest sample), so the convolution
doesn't delay the speech: latency metrics (#14) anchor on when speech ends in the clip, and a
shifted signal would charge the RIR's propagation delay to the provider. The output is trimmed
to the input length and scaled back to the input's power over the speech region, so reverb
changes the sound, not the level.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from harness.audio import Int16Array
from harness.augment.noise import Region, power


@dataclass(frozen=True)
class Reverbed:
    samples: Int16Array
    direct_index: int  # RIR sample taken as the direct path
    level_scale: float


def convolve(speech: Int16Array, rir: Int16Array, region: Region) -> Reverbed:
    if len(rir) == 0 or not np.any(rir):
        raise ValueError("empty or silent impulse response")
    s = speech.astype(np.float64)
    h = rir.astype(np.float64)
    direct = int(np.argmax(np.abs(h)))
    size = len(s) + len(h) - 1
    nfft = 1 << (size - 1).bit_length()
    full = np.fft.irfft(np.fft.rfft(s, nfft) * np.fft.rfft(h, nfft), nfft)[:size]
    wet = full[direct : direct + len(s)]
    p_in, p_out = power(s[region.start : region.end]), power(wet[region.start : region.end])
    scale = float(np.sqrt(p_in / p_out)) if p_out > 0 else 1.0
    out = wet * scale
    peak = float(np.max(np.abs(out)))
    if peak > 32767.0:
        scale *= 32767.0 / peak
        out = wet * scale
    samples = np.round(out).clip(-32768, 32767).astype(np.int16)
    return Reverbed(samples, direct, scale)
