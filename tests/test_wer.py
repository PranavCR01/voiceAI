import pytest

from harness.metrics.wer import (
    AlignmentChunk,
    UttScore,
    mean_utt_wer,
    pooled_wer,
    score_utterance,
)


@pytest.mark.parametrize(
    ("ref", "hyp", "s", "d", "i", "hits"),
    [
        # takes->take substituted, "daily" deleted
        ("the patient takes metformin daily", "the patient take metformin", 1, 1, 0, 3),
        # "please" and "now" inserted
        ("call me back", "please call me back now", 0, 0, 2, 3),
        # pressure->pleasure substituted, "is" deleted
        ("blood pressure is high", "blood pleasure high", 1, 1, 0, 2),
    ],
)
def test_hand_computed_counts(ref: str, hyp: str, s: int, d: int, i: int, hits: int) -> None:
    score = score_utterance(ref, hyp, normalized=True)
    assert (score.substitutions, score.deletions, score.insertions, score.hits) == (s, d, i, hits)
    assert score.n_ref == len(ref.split())
    assert score.wer == pytest.approx((s + d + i) / len(ref.split()))


def test_alignment_and_ref_token_hits() -> None:
    score = score_utterance("blood pressure is high", "blood pleasure high", normalized=True)
    assert score.alignment[0] == AlignmentChunk("equal", 0, 1, 0, 1)
    assert score.ref_token_hits() == (True, False, False, True)


def test_normalization_applied_by_default() -> None:
    score = score_utterance("Twenty-five milligrams, twice daily.", "25 milligrams twice daily")
    assert score.errors == 0


def test_tokenization_matches_alignment_with_odd_whitespace() -> None:
    score = score_utterance("a\tb\n c", "a  b c", normalized=True)
    assert score.ref_tokens == ("a", "b", "c") and score.errors == 0


def test_empty_reference_counts_insertions() -> None:
    score = score_utterance("", "hello there", normalized=True)
    assert (score.n_ref, score.insertions, score.wer) == (0, 2, None)


def test_both_empty() -> None:
    score = score_utterance("", "", normalized=True)
    assert (score.n_ref, score.errors, score.wer, score.alignment) == (0, 0, None, ())


def test_empty_hypothesis_is_all_deletions() -> None:
    score = score_utterance("a b c", "", normalized=True)
    assert (score.deletions, score.wer) == (3, 1.0)


def test_pooled_and_mean_diverge_on_short_turns() -> None:
    long_ref = " ".join(f"w{k}" for k in range(20))
    scores = [score_utterance(long_ref, long_ref, normalized=True)] + [
        score_utterance("yes", "yeah", normalized=True) for _ in range(3)
    ]
    assert pooled_wer(scores) == pytest.approx(3 / 23)
    assert mean_utt_wer(scores) == pytest.approx(3 / 4)


def test_empty_reference_excluded_from_mean_but_counted_in_pooled() -> None:
    scores = [
        score_utterance("a b", "a b", normalized=True),
        score_utterance("", "noise", normalized=True),
    ]
    assert mean_utt_wer(scores) == 0.0
    assert pooled_wer(scores) == pytest.approx(1 / 2)


def test_undefined_aggregates_raise() -> None:
    empty: list[UttScore] = [score_utterance("", "x", normalized=True)]
    with pytest.raises(ValueError, match="no reference words"):
        pooled_wer(empty)
    with pytest.raises(ValueError, match="no non-empty references"):
        mean_utt_wer(empty)
