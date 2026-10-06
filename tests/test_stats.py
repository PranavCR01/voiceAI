import numpy as np
import pytest

from harness.metrics.stats import (
    Interval,
    distinguishable,
    holm,
    paired_bootstrap,
    wilson_interval,
)

N_UTT = 300


def _utts(seed: int = 0) -> np.ndarray:
    return np.random.default_rng(seed).integers(3, 20, size=N_UTT)


def _errors(n_ref: np.ndarray, rate: float, seed: int) -> np.ndarray:
    return np.random.default_rng(seed).binomial(n_ref, rate)


# --- Wilson -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("k", "n", "low", "high"),
    [
        (0, 10, 0.0, 0.2775327998628899),
        (5, 10, 0.2365931019, 0.7634068981),
        (10, 10, 0.7224672001371101, 1.0),
    ],
)
def test_wilson_reference_values(k: int, n: int, low: float, high: float) -> None:
    iv = wilson_interval(k, n)
    assert iv.low == pytest.approx(low, abs=1e-6)
    assert iv.high == pytest.approx(high, abs=1e-6)
    assert iv.estimate == k / n


@pytest.mark.parametrize(("k", "n"), [(0, 0), (-1, 5), (6, 5)])
def test_wilson_rejects_bad_counts(k: int, n: int) -> None:
    with pytest.raises(ValueError):
        wilson_interval(k, n)


# --- paired bootstrap ---------------------------------------------------------


def test_identical_systems_are_not_distinguishable() -> None:
    n = _utts()
    e = _errors(n, 0.1, seed=1)
    res = paired_bootstrap({"a": e, "b": e.copy()}, n, seed=7, n_resamples=2_000)
    diff = res.differences[("a", "b")]
    assert diff.interval.contains(0.0)
    assert not diff.distinguishable
    assert diff.p_value == 1.0


def test_clearly_different_systems_are_distinguishable() -> None:
    n = _utts()
    res = paired_bootstrap(
        {"good": _errors(n, 0.05, seed=1), "bad": _errors(n, 0.25, seed=2)},
        n,
        seed=7,
        n_resamples=2_000,
    )
    diff = res.differences[("bad", "good")]  # keys are sorted system names
    assert diff.distinguishable
    assert diff.interval.low > 0
    assert diff.p_value < 0.01
    assert diff.p_value == pytest.approx(2 / 2_001)  # never exactly 0: floor is 2/(B+1)


def test_point_estimate_is_full_data_pooled_wer() -> None:
    n = np.array([10, 5, 5])
    e = np.array([1, 2, 0])
    res = paired_bootstrap({"x": e}, n, seed=0, n_resamples=100)
    assert res.systems["x"].estimate == pytest.approx(3 / 20)
    assert res.systems["x"].low <= res.systems["x"].estimate <= res.systems["x"].high


def test_same_seed_same_output_different_seed_different_output() -> None:
    n = _utts()
    errs = {"a": _errors(n, 0.1, 1), "b": _errors(n, 0.12, 2)}
    r1 = paired_bootstrap(errs, n, seed=42, n_resamples=1_500)
    r2 = paired_bootstrap(errs, n, seed=42, n_resamples=1_500)
    r3 = paired_bootstrap(errs, n, seed=43, n_resamples=1_500)
    assert r1 == r2
    assert r1.systems["a"] != r3.systems["a"]


def test_cluster_bootstrap_is_wider_when_errors_cluster_by_speaker() -> None:
    rng = np.random.default_rng(3)
    speakers = np.repeat(np.arange(10), 30)
    n = rng.integers(5, 15, size=speakers.size)
    speaker_rate = rng.uniform(0.0, 0.5, size=10)  # some speakers are much harder than others
    e = rng.binomial(n, speaker_rate[speakers])
    iid = paired_bootstrap({"x": e}, n, seed=1, n_resamples=3_000).systems["x"]
    clustered = paired_bootstrap(
        {"x": e}, n, seed=1, n_resamples=3_000, cluster_ids=speakers.tolist()
    )
    assert clustered.n_clusters == 10
    cl = clustered.systems["x"]
    assert (cl.high - cl.low) > 1.5 * (iid.high - iid.low)


def test_all_pairs_reported_once() -> None:
    n = _utts()
    errs = {s: _errors(n, 0.1, i) for i, s in enumerate(["c", "a", "b"])}
    res = paired_bootstrap(errs, n, seed=0, n_resamples=200)
    assert set(res.differences) == {("a", "b"), ("a", "c"), ("b", "c")}


def test_empty_reference_utterances_are_handled() -> None:
    n = np.array([0, 0, 0, 10])
    e = np.array([1, 0, 0, 2])
    res = paired_bootstrap({"x": e}, n, seed=0, n_resamples=500)
    assert res.systems["x"].estimate == pytest.approx(3 / 10)
    assert res.dropped_resamples > 0  # some resamples drew only empty references
    assert res.dropped_resamples < 500


@pytest.mark.parametrize(
    ("errors", "n_ref", "kwargs", "message"),
    [
        ({}, [1], {}, "no systems"),
        ({"a": [1]}, [], {}, "no utterances"),
        ({"a": [0]}, [0], {}, "no reference words"),
        ({"a": [1, 2]}, [3], {}, "must have length"),
        ({"a": [-1]}, [3], {}, "non-negative"),
        ({"a": [1]}, [3], {"cluster_ids": ["s1", "s2"]}, "cluster_ids"),
        ({"a": [1]}, [3], {"n_resamples": 0}, "n_resamples"),
        ({"a": [1]}, [3], {"confidence": 1.0}, "confidence"),
    ],
)
def test_bootstrap_validation(
    errors: dict[str, list[int]], n_ref: list[int], kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        paired_bootstrap(errors, n_ref, seed=0, **kwargs)  # type: ignore[arg-type]


# --- distinguishable / Holm ---------------------------------------------------


def test_distinguishable() -> None:
    assert distinguishable(Interval(0.02, 0.01, 0.03))
    assert distinguishable(Interval(-0.02, -0.03, -0.01))
    assert not distinguishable(Interval(0.0, -0.01, 0.01))
    assert not distinguishable(Interval(0.01, 0.0, 0.02))  # touching zero is not excluding it


def test_holm_hand_worked_example() -> None:
    # Sorted: 0.005 (x4=0.02), 0.01 (x3=0.03), 0.03 (x2=0.06), 0.04 (x1=0.04 -> cummax 0.06)
    adjusted, reject = holm([0.01, 0.04, 0.03, 0.005])
    assert adjusted == pytest.approx([0.03, 0.06, 0.06, 0.02])
    assert reject == [True, False, False, True]


def test_holm_caps_at_one_and_handles_empty() -> None:
    assert holm([0.6, 0.9])[0] == [1.0, 1.0]
    assert holm([]) == ([], [])
    with pytest.raises(ValueError):
        holm([1.5])
