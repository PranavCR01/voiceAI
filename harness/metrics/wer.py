"""Word error rate.

Pooled WER = sum(S + D + I) / sum(N) over all utterances is the headline number; mean
per-utterance WER is reported alongside (see docs/DECISIONS.md).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

import jiwer

from harness.metrics.normalize import DateOrder, normalize

Op = Literal["equal", "substitute", "delete", "insert"]


@dataclass(frozen=True)
class AlignmentChunk:
    """A run of one edit operation; indices are half-open token spans."""

    op: Op
    ref_start: int
    ref_end: int
    hyp_start: int
    hyp_end: int


@dataclass(frozen=True)
class UttScore:
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    substitutions: int
    deletions: int
    insertions: int
    hits: int
    alignment: tuple[AlignmentChunk, ...]

    @property
    def n_ref(self) -> int:
        return len(self.ref_tokens)

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def wer(self) -> float | None:
        """None for an empty reference: WER is undefined there."""
        return self.errors / self.n_ref if self.n_ref else None

    def ref_token_hits(self) -> tuple[bool, ...]:
        """For each reference token, whether it was recognized correctly."""
        hits = [False] * self.n_ref
        for c in self.alignment:
            if c.op == "equal":
                hits[c.ref_start : c.ref_end] = [True] * (c.ref_end - c.ref_start)
        return tuple(hits)


def score_utterance(
    ref: str,
    hyp: str,
    *,
    normalized: bool = False,
    equivalences: bool = True,
    date_order: DateOrder = "mdy",
) -> UttScore:
    """Align ref and hyp.

    Both are normalized first (Whisper + equivalence layer) unless `normalized=True`.
    `equivalences=False` gives plain-Whisper WER, comparable with public leaderboards.
    """
    if not normalized:
        ref = normalize(ref, equivalences=equivalences, date_order=date_order)
        hyp = normalize(hyp, equivalences=equivalences, date_order=date_order)
    ref_tokens, hyp_tokens = tuple(ref.split()), tuple(hyp.split())
    if not ref_tokens and not hyp_tokens:
        return UttScore(ref_tokens, hyp_tokens, 0, 0, 0, 0, ())
    # Re-join so jiwer tokenizes exactly as ref_tokens/hyp_tokens do (any whitespace).
    out = jiwer.process_words(" ".join(ref_tokens), " ".join(hyp_tokens))
    alignment = tuple(
        AlignmentChunk(
            cast(Op, c.type), c.ref_start_idx, c.ref_end_idx, c.hyp_start_idx, c.hyp_end_idx
        )
        for c in out.alignments[0]
    )
    return UttScore(
        ref_tokens=ref_tokens,
        hyp_tokens=hyp_tokens,
        substitutions=out.substitutions,
        deletions=out.deletions,
        insertions=out.insertions,
        hits=out.hits,
        alignment=alignment,
    )


def pooled_wer(scores: Iterable[UttScore]) -> float:
    """Total errors / total reference words. Empty references contribute their insertions."""
    errors = n = 0
    for s in scores:
        errors += s.errors
        n += s.n_ref
    if n == 0:
        raise ValueError("pooled WER is undefined: no reference words")
    return errors / n


def mean_utt_wer(scores: Iterable[UttScore]) -> float:
    """Mean of per-utterance WER, excluding utterances with an empty reference."""
    wers = [s.wer for s in scores if s.wer is not None]
    if not wers:
        raise ValueError("mean utterance WER is undefined: no non-empty references")
    return sum(wers) / len(wers)
