"""Streaming latency metrics, computed from session traces only (harness/streaming/trace.py).

Anchoring: a moment in the audio (speech start/end, from #15) is mapped to the wall time at
which the chunk containing it was *sent*. The provider cannot react to audio it hasn't
received, and chunks go out whole, so latency is measured from that send time. A late chunk
therefore moves the anchor with it instead of being charged to the provider.

Per session, each metric is a `Measurement` with a status:
- `ok`: a value in ms;
- `timeout`: the event never came (no final, no endpoint); counted, never dropped;
- `not_applicable`: e.g. finalize latency in natural mode, endpoint delay in forced mode;
- `not_supported`: forced mode on a provider without an explicit finalize message;
- `missing_ground_truth`: no speech start/end known for this utterance.

Aggregates treat timeouts as +inf, so if more than 5% of sessions time out the p95 *is* the
timeout ("slower than we waited"), instead of a flattering number over the survivors.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from harness.metrics.stats import Interval, percentile_bootstrap
from harness.streaming.trace import Event, EventKind, SessionTrace

Status = Literal["ok", "timeout", "not_applicable", "not_supported", "missing_ground_truth"]
# How TTFS found "the final covering the last word".
TtfsBasis = Literal["word_timestamps", "last_final"]
# Words ending this long after the true speech end are not the speaker's last word (they are
# hallucinations or noise transcribed during silence), so they can't define TTFS.
LAST_WORD_TOLERANCE_MS = 300.0
METRICS = ("connection_setup", "first_partial", "ttfs", "finalize_latency", "endpoint_delay")


@dataclass(frozen=True)
class Measurement:
    status: Status
    value_ms: float | None = None
    basis: TtfsBasis | None = None  # TTFS only

    @staticmethod
    def ok(ns: int, basis: TtfsBasis | None = None) -> Measurement:
        return Measurement("ok", ns / 1e6, basis)


@dataclass(frozen=True)
class SessionLatency:
    config_id: str
    utt_id: str
    connection_setup: Measurement
    first_partial: Measurement
    ttfs: Measurement
    finalize_latency: Measurement
    endpoint_delay: Measurement
    premature_endpoints: int  # provider endpoints before the true speech end was sent

    def get(self, metric: str) -> Measurement:
        if metric not in METRICS:
            raise KeyError(metric)
        value: Measurement = getattr(self, metric)
        return value


def sent_at_ns(trace: SessionTrace, audio_offset_ms: float) -> int | None:
    """Wall time (t_ns) at which the chunk containing `audio_offset_ms` was sent."""
    chunk_ms = trace.meta.chunk_ms
    for e in trace.of(EventKind.AUDIO_SENT):
        assert e.audio_offset_ms is not None
        if e.audio_offset_ms <= audio_offset_ms < e.audio_offset_ms + chunk_ms:
            return e.t_ns
    return None


def _ttfs(finals: Sequence[Event], speech_end_ns: int, speech_end_ms: float) -> Measurement:
    """Time from the speech-end anchor to the final containing the speaker's last word.

    With word timings: the last word is the one ending latest, among words ending no later than
    `LAST_WORD_TOLERANCE_MS` after the true speech end; TTFS is the arrival of the first final
    that contains it (a trailing final with a filler or hallucination during silence is
    ignored). Without word timings: the last final after the anchor, labelled as such.
    """
    limit = speech_end_ms + LAST_WORD_TOLERANCE_MS
    candidates = [(w.end_ms, e.t_ns) for e in finals for w in (e.words or ()) if w.end_ms <= limit]
    if candidates:
        last_end = max(end for end, _ in candidates)
        arrival = min(t for end, t in candidates if end == last_end)
        return Measurement.ok(arrival - speech_end_ns, "word_timestamps")
    late = [e for e in finals if e.t_ns >= speech_end_ns]
    if late:
        return Measurement.ok(late[-1].t_ns - speech_end_ns, "last_final")
    return Measurement("timeout")


def session_latency(trace: SessionTrace) -> SessionLatency:
    meta = trace.meta
    start, ready = trace.first(EventKind.CONNECT_START), trace.first(EventKind.CONNECT_READY)
    setup = Measurement.ok(ready.t_ns - start.t_ns) if start and ready else Measurement("timeout")

    # First partial, from speech onset (or the first audio sent when onset is unknown).
    first_audio = trace.first(EventKind.AUDIO_SENT)
    onset = (
        sent_at_ns(trace, meta.speech_start_ms)
        if meta.speech_start_ms is not None
        else (first_audio.t_ns if first_audio else None)
    )
    if onset is None:
        first_partial = Measurement("missing_ground_truth")
    else:
        partial = trace.first(EventKind.PARTIAL, after_ns=onset - 1)
        first_partial = Measurement.ok(partial.t_ns - onset) if partial else Measurement("timeout")

    speech_end = sent_at_ns(trace, meta.speech_end_ms) if meta.speech_end_ms is not None else None
    finals = trace.of(EventKind.FINAL)
    endpoints = trace.of(EventKind.ENDPOINT)

    # TTFS: when the final containing the speaker's last word arrived.
    if speech_end is None or meta.speech_end_ms is None:
        ttfs = Measurement("missing_ground_truth")
    else:
        ttfs = _ttfs(finals, speech_end, meta.speech_end_ms)

    # Finalize latency: forced mode only.
    if meta.finalization_mode != "forced":
        finalize = Measurement("not_applicable")
    elif not meta.finalize_supported:
        finalize = Measurement("not_supported")
    else:
        sent = trace.first(EventKind.FINALIZE_SENT)
        reply = trace.first(EventKind.FINAL, after_ns=sent.t_ns - 1) if sent else None
        finalize = (
            Measurement.ok(reply.t_ns - sent.t_ns) if sent and reply else Measurement("timeout")
        )

    # Endpoint delay: natural mode only; endpoints before speech end are premature (#20).
    premature = 0
    if speech_end is None:
        endpoint = Measurement("missing_ground_truth")
    else:
        premature = sum(e.t_ns < speech_end for e in endpoints)
        if meta.finalization_mode != "natural":
            endpoint = Measurement("not_applicable")
        else:
            after = [e for e in endpoints if e.t_ns >= speech_end]
            endpoint = (
                Measurement.ok(after[0].t_ns - speech_end) if after else Measurement("timeout")
            )

    return SessionLatency(
        config_id=meta.config_id,
        utt_id=meta.utt_id,
        connection_setup=setup,
        first_partial=first_partial,
        ttfs=ttfs,
        finalize_latency=finalize,
        endpoint_delay=endpoint,
        premature_endpoints=premature,
    )


@dataclass(frozen=True)
class LatencySummary:
    metric: str
    n: int  # sessions where the metric applies (ok + timeout)
    n_timeout: int
    p50: Interval | None
    p95: Interval | None
    p99: Interval | None
    excluded: dict[str, int]  # not_applicable / not_supported / missing_ground_truth counts
    clustered: bool = False  # intervals resample whole clusters (speakers)
    # Width of the clustered p50 interval / width of the iid one. ~1: sessions behave as
    # independent; well above 1: latency clusters by speaker and iid intervals would be too
    # narrow. None when not clustered or when the iid interval has zero width.
    cluster_effect: float | None = None
    ttfs_basis: dict[str, int] = field(default_factory=dict)  # TTFS: sessions per basis

    @property
    def timeout_rate(self) -> float | None:
        return self.n_timeout / self.n if self.n else None


def summarize(
    sessions: Iterable[SessionLatency],
    metric: str,
    *,
    clusters: Mapping[str, Hashable] | None = None,
    seed: int = 0,
    n_resamples: int = 10_000,
    quantiles: Sequence[float] = (50, 95, 99),
) -> LatencySummary:
    """Percentiles with bootstrap CIs over sessions where the metric applies; timeouts = +inf.

    `clusters` maps utt_id -> cluster (normally the speaker); pass it to resample whole
    speakers, as the WER intervals do. Every included session must have a cluster.
    """
    values: list[float] = []
    cluster_ids: list[Hashable] = []
    n_timeout = 0
    excluded: dict[str, int] = {}
    basis: dict[str, int] = {}
    for s in sessions:
        m = s.get(metric)
        if m.status not in ("ok", "timeout"):
            excluded[m.status] = excluded.get(m.status, 0) + 1
            continue
        if m.status == "ok":
            assert m.value_ms is not None
            values.append(m.value_ms)
            if m.basis is not None:
                basis[m.basis] = basis.get(m.basis, 0) + 1
        else:
            values.append(math.inf)
            n_timeout += 1
        if clusters is not None:
            if s.utt_id not in clusters:
                raise KeyError(f"no cluster for {s.utt_id}")
            cluster_ids.append(clusters[s.utt_id])
    ids = cluster_ids if clusters is not None else None
    p = {
        q: percentile_bootstrap(values, q, seed=seed, n_resamples=n_resamples, cluster_ids=ids)
        if values
        else None
        for q in quantiles
    }
    effect = None
    if ids is not None and values and p.get(50) is not None:
        iid = percentile_bootstrap(values, 50, seed=seed, n_resamples=n_resamples)
        clustered = p[50]
        assert clustered is not None
        iid_width, clustered_width = iid.high - iid.low, clustered.high - clustered.low
        if iid_width > 0 and math.isfinite(iid_width) and math.isfinite(clustered_width):
            effect = clustered_width / iid_width
    return LatencySummary(
        metric=metric,
        n=len(values),
        n_timeout=n_timeout,
        p50=p.get(50),
        p95=p.get(95),
        p99=p.get(99),
        excluded=dict(sorted(excluded.items())),
        clustered=ids is not None,
        cluster_effect=effect,
        ttfs_basis=dict(sorted(basis.items())),
    )
