import math
from pathlib import Path

import numpy as np
import pytest

from harness.metrics.latency import Measurement, SessionLatency, session_latency, summarize
from harness.metrics.stats import percentile_bootstrap
from harness.streaming.trace import (
    Event,
    EventKind,
    Recorder,
    SessionMeta,
    SessionTrace,
    read_trace,
    trace_filename,
    write_trace,
)

FIX = Path(__file__).parent / "fixtures" / "traces"
MS = 1_000_000


def load(name: str) -> SessionTrace:
    return read_trace(FIX / f"{name}.jsonl")


def ok(ms: float) -> Measurement:
    return Measurement("ok", ms)


# --- per-session metrics on hand-specified traces -----------------------------------------
# All fixtures: 100 ms chunks, chunk k sent at 50 + 100k ms; speech 150-750 ms of audio,
# so speech onset is in chunk 1 (sent at 150 ms) and speech end in chunk 7 (sent at 750 ms).


def test_clean_session() -> None:
    s = session_latency(load("clean"))
    assert s.connection_setup == ok(50)
    assert s.first_partial == ok(250)  # partial at 400 - onset chunk sent at 150
    assert s.ttfs == ok(250)  # last final at 1000 - 750
    assert s.endpoint_delay == ok(350)  # endpoint at 1100 - 750
    assert s.finalize_latency.status == "not_applicable"
    assert s.premature_endpoints == 0


def test_late_final() -> None:
    assert session_latency(load("late_final")).ttfs == ok(2000)


def test_no_final_is_a_timeout_not_a_drop() -> None:
    s = session_latency(load("no_final"))
    assert s.ttfs.status == "timeout" and s.ttfs.value_ms is None
    assert s.endpoint_delay == ok(350)


def test_early_endpoint_counted_as_premature() -> None:
    s = session_latency(load("early_endpoint"))
    assert s.premature_endpoints == 1
    assert s.endpoint_delay == ok(450)  # the first endpoint after speech end, at 1200


def test_forced_finalize() -> None:
    s = session_latency(load("forced"))
    assert s.finalize_latency == ok(148)  # final at 900 - finalize sent at 752
    assert s.ttfs == ok(150)
    assert s.endpoint_delay.status == "not_applicable"


def test_forced_without_final_is_timeout_and_unsupported_is_labelled() -> None:
    trace = load("forced")
    no_final = trace.model_copy(
        update={"events": tuple(e for e in trace.events if e.kind is not EventKind.FINAL)}
    )
    assert session_latency(no_final).finalize_latency.status == "timeout"
    meta = trace.meta.model_copy(update={"finalize_supported": False})
    unsupported = trace.model_copy(update={"meta": meta})
    assert session_latency(unsupported).finalize_latency.status == "not_supported"


def test_anchor_moves_with_a_late_chunk() -> None:
    trace = load("clean")
    events = tuple(
        e.model_copy(update={"t_ns": 790 * MS})
        if e.kind is EventKind.AUDIO_SENT and e.chunk_index == 7
        else e
        for e in trace.events
    )
    late = trace.model_copy(update={"events": events})
    assert session_latency(late).ttfs == ok(210)  # final at 1000 - chunk 7 actually sent at 790


def test_missing_ground_truth() -> None:
    trace = load("clean")
    meta = trace.meta.model_copy(update={"speech_start_ms": None, "speech_end_ms": None})
    s = session_latency(trace.model_copy(update={"meta": meta}))
    assert s.ttfs.status == "missing_ground_truth"
    assert s.endpoint_delay.status == "missing_ground_truth"
    assert s.first_partial == ok(350)  # falls back to the first audio sent, at 50


# --- aggregation ----------------------------------------------------------------------------


def all_sessions() -> list[SessionLatency]:
    return [
        session_latency(load(n))
        for n in ("clean", "late_final", "no_final", "early_endpoint", "forced")
    ]


def test_summary_counts_timeouts_as_infinite() -> None:
    ttfs = summarize(all_sessions(), "ttfs", n_resamples=500)
    assert (ttfs.n, ttfs.n_timeout) == (5, 1)
    assert ttfs.timeout_rate == pytest.approx(0.2)
    assert ttfs.p50 is not None and ttfs.p50.estimate == 250  # [150, 250, 250, 2000, inf]
    assert ttfs.p95 is not None and math.isinf(ttfs.p95.estimate)  # >5% timed out


def test_summary_excludes_inapplicable_sessions() -> None:
    delay = summarize(all_sessions(), "endpoint_delay", n_resamples=500)
    assert delay.n == 4 and delay.excluded == {"not_applicable": 1}
    finalize = summarize(all_sessions(), "finalize_latency", n_resamples=500)
    assert finalize.n == 1 and finalize.excluded == {"not_applicable": 4}


def test_summary_of_nothing() -> None:
    s = summarize([], "ttfs")
    assert (s.n, s.p50, s.timeout_rate) == (0, None, None)


def test_unknown_metric() -> None:
    with pytest.raises(KeyError):
        all_sessions()[0].get("latency")


# --- percentile bootstrap ----------------------------------------------------------------


def test_percentile_is_an_observed_value() -> None:
    assert percentile_bootstrap([10, 20, 30, 40], 50, seed=0, n_resamples=200).estimate == 20
    assert percentile_bootstrap([10, 20, 30, 40], 100, seed=0, n_resamples=200).estimate == 40


def test_percentile_constant_values_give_a_degenerate_interval() -> None:
    iv = percentile_bootstrap([5.0] * 20, 95, seed=0, n_resamples=200)
    assert (iv.estimate, iv.low, iv.high) == (5.0, 5.0, 5.0)


def test_percentile_interval_contains_estimate_and_is_deterministic() -> None:
    values = np.random.default_rng(0).gamma(2.0, 100.0, size=300)
    a = percentile_bootstrap(values, 95, seed=1, n_resamples=2000)
    b = percentile_bootstrap(values, 95, seed=1, n_resamples=2000)
    assert a == b and a.low <= a.estimate <= a.high


def test_percentile_handles_infinity() -> None:
    iv = percentile_bootstrap([1.0, 2.0, math.inf, math.inf], 50, seed=0, n_resamples=200)
    assert iv.estimate == 2.0 and not math.isnan(iv.high)


@pytest.mark.parametrize("bad", [[], [1.0, math.nan]])
def test_percentile_rejects_bad_input(bad: list[float]) -> None:
    with pytest.raises(ValueError):
        percentile_bootstrap(bad, 50, seed=0)


# --- trace schema -------------------------------------------------------------------------


def test_round_trip(tmp_path: Path) -> None:
    trace = load("forced")
    write_trace(tmp_path / "t.jsonl", trace)
    assert read_trace(tmp_path / "t.jsonl") == trace
    assert trace.text() == "hello there"


@pytest.mark.parametrize(
    ("events", "message"),
    [
        (
            [Event(kind=EventKind.CLOSED, t_ns=5), Event(kind=EventKind.CONNECT_START, t_ns=1)],
            "time order",
        ),
        (
            [
                Event(kind=EventKind.AUDIO_SENT, t_ns=1, chunk_index=0, audio_offset_ms=20),
                Event(kind=EventKind.AUDIO_SENT, t_ns=2, chunk_index=1, audio_offset_ms=20),
            ],
            "offsets must increase",
        ),
    ],
)
def test_trace_validation(events: list[Event], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        SessionTrace(meta=SessionMeta(config_id="c", utt_id="u", chunk_ms=20), events=tuple(events))


@pytest.mark.parametrize(
    "fields",
    [
        {"kind": "audio_sent", "t_ns": 0},
        {"kind": "final", "t_ns": 0},
        {"kind": "partial", "t_ns": -1, "text": "x"},
    ],
)
def test_event_validation(fields: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        Event.model_validate(fields)


def test_recorder_orders_events_and_uses_supplied_times() -> None:
    rec = Recorder(SessionMeta(config_id="c", utt_id="u", chunk_ms=20))
    with pytest.raises(RuntimeError):
        rec.record(EventKind.CLOSED)
    rec.start()
    t0 = rec._t0
    assert t0 is not None
    rec.record(EventKind.FINAL, at_ns=t0 + 30 * MS, text="b")
    rec.record(EventKind.AUDIO_SENT, at_ns=t0 + 10 * MS, chunk_index=0, audio_offset_ms=0)
    trace = rec.trace()
    assert [e.kind for e in trace.events] == [
        EventKind.CONNECT_START,
        EventKind.AUDIO_SENT,
        EventKind.FINAL,
    ]
    assert trace.events[1].t_ns == 10 * MS


def test_trace_filename() -> None:
    assert trace_filename("primock57:day1:patient:0001") == "primock57__day1__patient__0001.jsonl"
