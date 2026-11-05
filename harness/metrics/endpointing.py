"""Endpointing outcomes from streaming traces (#20): premature, correct, late/missed.

Natural-mode sessions only (the provider's endpointing decides). Each session gets exactly one
outcome, judged against the moment the chunk containing the true speech end was *sent*
(the same anchor as TTFS, harness/streaming/README.md):

- **premature**: an `endpoint` event before the anchor, i.e. while the caller was still talking
  or pausing mid-sentence ("my number is ... 07700"). For a turn labelled incomplete (the caller
  hasn't finished, as in smart-turn's incomplete samples) *any* endpoint is premature.
- **correct**: no premature endpoint, and the first endpoint at/after the anchor arrives within
  `late_after_ms` (default 3 s); its delay is the endpoint delay.
- **late**: no endpoint within `late_after_ms` of the anchor (missed, or too slow to be useful).
- **unscorable**: no ground-truth speech end, or not a natural-mode session; counted, not rated.

Rates are over scorable sessions with Wilson intervals (not clustered, like the empty-on-speech
rate); delay percentiles use the speaker-clustered bootstrap.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Literal

from harness.metrics.latency import sent_at_ns
from harness.metrics.stats import Interval, percentile_bootstrap, wilson_interval
from harness.streaming.trace import EventKind, SessionTrace

Outcome = Literal["premature", "correct", "late", "unscorable"]
DEFAULT_LATE_AFTER_MS = 3000.0


@dataclass(frozen=True)
class EndpointOutcome:
    utt_id: str
    outcome: Outcome
    delay_ms: float | None = None  # correct only
    premature_count: int = 0  # endpoints before the anchor (or any, for incomplete turns)


def classify(
    trace: SessionTrace, *, complete: bool = True, late_after_ms: float = DEFAULT_LATE_AFTER_MS
) -> EndpointOutcome:
    meta = trace.meta
    if meta.finalization_mode != "natural":
        return EndpointOutcome(meta.utt_id, "unscorable")
    endpoints = [e.t_ns for e in trace.of(EventKind.ENDPOINT)]
    if not complete:
        # The caller never finished: the right behaviour is to keep listening.
        if endpoints:
            return EndpointOutcome(meta.utt_id, "premature", premature_count=len(endpoints))
        return EndpointOutcome(meta.utt_id, "correct")
    if meta.speech_end_ms is None:
        return EndpointOutcome(meta.utt_id, "unscorable")
    anchor = sent_at_ns(trace, meta.speech_end_ms)
    if anchor is None:
        return EndpointOutcome(meta.utt_id, "unscorable")
    early = [t for t in endpoints if t < anchor]
    if early:
        return EndpointOutcome(meta.utt_id, "premature", premature_count=len(early))
    after = [t for t in endpoints if t >= anchor]
    if after and (after[0] - anchor) / 1e6 <= late_after_ms:
        return EndpointOutcome(meta.utt_id, "correct", delay_ms=(after[0] - anchor) / 1e6)
    return EndpointOutcome(meta.utt_id, "late")


@dataclass(frozen=True)
class EndpointSummary:
    sessions: int  # scorable
    unscorable: int
    premature: Interval | None  # rate with Wilson CI
    late: Interval | None
    correct: Interval | None
    delay_p50: Interval | None  # ms, correct endpoints only
    delay_p95: Interval | None
    counts: dict[str, int] = field(default_factory=dict)


def summarize_endpoints(
    outcomes: Iterable[EndpointOutcome],
    *,
    clusters: Mapping[str, Hashable] | None = None,
    seed: int = 0,
    n_resamples: int = 10_000,
) -> EndpointSummary:
    items = list(outcomes)
    counts = {
        k: sum(o.outcome == k for o in items)
        for k in ("premature", "correct", "late", "unscorable")
    }
    n = len(items) - counts["unscorable"]

    def rate(k: str) -> Interval | None:
        return wilson_interval(counts[k], n) if n else None

    delays = [o for o in items if o.outcome == "correct" and o.delay_ms is not None]
    values = [o.delay_ms for o in delays if o.delay_ms is not None]
    ids = [clusters[o.utt_id] for o in delays] if clusters is not None else None

    def pct(q: float) -> Interval | None:
        if not values:
            return None
        return percentile_bootstrap(values, q, seed=seed, n_resamples=n_resamples, cluster_ids=ids)

    return EndpointSummary(
        sessions=n,
        unscorable=counts["unscorable"],
        premature=rate("premature"),
        late=rate("late"),
        correct=rate("correct"),
        delay_p50=pct(50),
        delay_p95=pct(95),
        counts=counts,
    )
