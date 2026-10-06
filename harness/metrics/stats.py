"""Confidence intervals and multiple-comparison correction.

- Paired bootstrap for pooled WER: every system is scored on the same resamples of the same
  utterances, so pairwise differences are paired. Resampling can be by cluster (speaker) when
  utterances from one speaker are correlated.
- Wilson score interval for proportions (entity recall, endpoint error rates, check pass rates).
- Holm step-down correction when claiming many pairwise wins at once.

All randomness goes through an explicit seed: same inputs + same seed -> identical output.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass
from itertools import combinations
from statistics import NormalDist

import numpy as np
from numpy.typing import ArrayLike, NDArray

FloatArray = NDArray[np.float64]

# Resamples are processed in chunks to bound memory at (chunk x clusters) weights.
_CHUNK = 1_000


@dataclass(frozen=True)
class Interval:
    estimate: float
    low: float
    high: float

    def contains(self, value: float) -> bool:
        return self.low <= value <= self.high


@dataclass(frozen=True)
class Difference:
    """Pooled WER of system `a` minus system `b`; negative means `a` is better."""

    a: str
    b: str
    interval: Interval
    p_value: float  # two-sided bootstrap p-value

    @property
    def distinguishable(self) -> bool:
        return distinguishable(self.interval)


@dataclass(frozen=True)
class BootstrapResult:
    systems: dict[str, Interval]
    differences: dict[tuple[str, str], Difference]
    n_resamples: int
    n_clusters: int
    dropped_resamples: int  # resamples with zero reference words (only possible with empty refs)


def distinguishable(diff: Interval) -> bool:
    """True when the difference interval excludes zero."""
    return diff.low > 0 or diff.high < 0


def _as_1d(name: str, values: ArrayLike) -> FloatArray:
    arr = np.asarray(values, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if np.any(arr < 0) or not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must be finite and non-negative")
    return arr


def paired_bootstrap(
    errors: Mapping[str, ArrayLike],
    n_ref: ArrayLike,
    *,
    seed: int,
    n_resamples: int = 10_000,
    cluster_ids: Sequence[Hashable] | None = None,
    confidence: float = 0.95,
) -> BootstrapResult:
    """Percentile intervals for each system's pooled WER and every pairwise difference.

    `errors[system][i]` is S+D+I for utterance i; `n_ref[i]` its reference word count (the same
    references for every system, which is what makes the bootstrap paired). With `cluster_ids`,
    whole clusters (e.g. speakers) are resampled instead of utterances.

    The p-value for a difference is two-sided: 2 x the smaller share of resampled differences on
    either side of zero, with the +1 correction ((count + 1) / (B + 1)) so it is never reported
    as exactly 0 from a finite number of resamples; capped at 1.
    """
    if not errors:
        raise ValueError("no systems given")
    if n_resamples < 1:
        raise ValueError("n_resamples must be >= 1")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")
    n = _as_1d("n_ref", n_ref)
    if n.size == 0:
        raise ValueError("no utterances given")
    if n.sum() == 0:
        raise ValueError("pooled WER is undefined: no reference words")
    names = sorted(errors)
    errs = np.stack([_as_1d(f"errors[{s!r}]", errors[s]) for s in names])
    if errs.shape[1] != n.size:
        raise ValueError(f"every errors array must have length {n.size} (len(n_ref))")

    # Collapse to per-cluster sums; without clusters every utterance is its own cluster.
    if cluster_ids is None:
        cl_errs, cl_n = errs, n
    else:
        if len(cluster_ids) != n.size:
            raise ValueError(f"cluster_ids must have length {n.size} (len(n_ref))")
        index = {c: k for k, c in enumerate(dict.fromkeys(cluster_ids))}
        codes = np.fromiter((index[c] for c in cluster_ids), dtype=np.intp, count=n.size)
        k = len(index)
        cl_n = np.bincount(codes, weights=n, minlength=k)
        cl_errs = np.stack([np.bincount(codes, weights=row, minlength=k) for row in errs])
    n_clusters = cl_n.size

    rng = np.random.default_rng(seed)
    probs = np.full(n_clusters, 1.0 / n_clusters)
    wer = np.empty((len(names), n_resamples))
    for start in range(0, n_resamples, _CHUNK):
        size = min(_CHUNK, n_resamples - start)
        weights = rng.multinomial(n_clusters, probs, size=size).astype(np.float64)
        denom = weights @ cl_n
        with np.errstate(divide="ignore", invalid="ignore"):
            wer[:, start : start + size] = (weights @ cl_errs.T).T / denom
    valid = np.isfinite(wer[0])
    wer = wer[:, valid]
    if wer.shape[1] == 0:
        raise ValueError("every resample had zero reference words")

    tail = (1 - confidence) / 2 * 100
    qs = (tail, 100 - tail)
    point = errs.sum(axis=1) / n.sum()

    systems = {}
    for i, s in enumerate(names):
        lo, hi = np.percentile(wer[i], qs)
        systems[s] = Interval(float(point[i]), float(lo), float(hi))

    differences = {}
    for (i, a), (j, b) in combinations(enumerate(names), 2):
        d = wer[i] - wer[j]
        lo, hi = np.percentile(d, qs)
        b_valid = d.size
        tail_count = min(int(np.count_nonzero(d <= 0)), int(np.count_nonzero(d >= 0)))
        p = min(1.0, 2 * (tail_count + 1) / (b_valid + 1))
        differences[(a, b)] = Difference(
            a, b, Interval(float(point[i] - point[j]), float(lo), float(hi)), p
        )

    return BootstrapResult(
        systems=systems,
        differences=differences,
        n_resamples=n_resamples,
        n_clusters=n_clusters,
        dropped_resamples=int((~valid).sum()),
    )


def wilson_interval(k: int, n: int, *, confidence: float = 0.95) -> Interval:
    """Wilson score interval for k successes out of n trials."""
    if n <= 0:
        raise ValueError("n must be > 0")
    if not 0 <= k <= n:
        raise ValueError("k must be in [0, n]")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be in (0, 1)")
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return Interval(p, max(0.0, center - half), min(1.0, center + half))


def holm(p_values: Sequence[float], *, alpha: float = 0.05) -> tuple[list[float], list[bool]]:
    """Holm step-down adjusted p-values and reject flags, in the input order."""
    m = len(p_values)
    if any(not 0 <= p <= 1 for p in p_values):
        raise ValueError("p-values must be in [0, 1]")
    order = sorted(range(m), key=lambda i: p_values[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running
    return adjusted, [p <= alpha for p in adjusted]
