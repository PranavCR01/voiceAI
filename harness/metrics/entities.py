"""Entity tagging and entity-level scoring, driven by the use-case profile.

The categories come from the profile (`entities:`), never from this module: a healthcare profile
asks for medications and dosages, a billing profile for account numbers and amounts. Rules are
written up in harness/metrics/ENTITIES.md.

Tagging runs on the *normalized* reference (same normalizer as WER), so entity spans line up
with the WER alignment. Per entity we report:
- recovered: every reference token in the span was recognized (strict, token level);
- character errors: edit distance between the span and the hypothesis tokens aligned to it,
  so one wrong digit in a 10-digit phone number costs 1/10, not the whole entity;
- formatted (numeric builtins only): the raw hypothesis carries the entity's numbers as digits,
  i.e. in a form a downstream system can use without re-parsing words.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz.distance import Levenshtein

from harness.metrics.normalize import DateOrder, normalize
from harness.metrics.stats import Interval, wilson_interval
from harness.metrics.wer import UttScore
from recommender.profile import Builtin, EntityCategory, EntityKind, read_lexicon

_MONTH = (
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)"
)
_NUM = r"(?:\d+(?:\.\d+)?|one)"  # Whisper keeps a standalone 1 as "one"
_TOKEN_START, _TOKEN_END = r"(?<!\S)", r"(?!\S)"

# Patterns over normalized text. Alternatives are ordered longest first.
_BUILTIN_PATTERNS: dict[Builtin, str] = {
    Builtin.NUMBER: r"[$£€]?\d[\d.,]*%?",
    # After normalization a phone number is one token of >= 7 digits (digit runs are joined).
    Builtin.PHONE: r"\d{7,15}",
    Builtin.DATE: (
        rf"{_MONTH} \d{{1,2}} \d{{4}}"
        rf"|\d{{1,2}} (?:of )?{_MONTH} \d{{4}}"
        rf"|\d{{1,2}} (?:of )?{_MONTH}"
        rf"|{_MONTH} \d{{1,2}}"
        rf"|{_MONTH} \d{{4}}"
    ),
    Builtin.DOSAGE: (
        rf"{_NUM} (?:mg|mcg|ml|g|iu|units?|puffs?|tablets?|capsules?|drops?|sachets?|sprays?)"
    ),
    Builtin.DURATION: rf"{_NUM} (?:seconds?|minutes?|hours?|days?|weeks?|months?|years?)",
}
_NUMERIC_BUILTINS = frozenset(_BUILTIN_PATTERNS)  # all builtins carry numbers


@dataclass(frozen=True)
class EntitySpan:
    category: str
    start: int  # token index in the normalized reference, inclusive
    end: int  # exclusive
    text: str


@dataclass(frozen=True)
class CategorySpec:
    name: str
    kind: EntityKind
    builtin: Builtin | None = None
    pattern: re.Pattern[str] | None = None
    terms: tuple[tuple[str, ...], ...] = ()  # normalized lexicon terms as token tuples

    @property
    def numeric(self) -> bool:
        return self.builtin in _NUMERIC_BUILTINS


@dataclass(frozen=True)
class EntityOutcome:
    span: EntitySpan
    recovered: bool
    char_errors: int
    char_total: int
    formatted: bool | None  # None for non-numeric categories or when no raw hypothesis given


@dataclass(frozen=True)
class CategorySummary:
    category: str
    n: int
    recovered: int
    recall: Interval
    char_errors: int
    char_total: int
    formatted: int | None
    formatted_accuracy: Interval | None

    @property
    def cer(self) -> float | None:
        return self.char_errors / self.char_total if self.char_total else None


def _token_starts(tokens: Sequence[str]) -> list[int]:
    starts, pos = [], 0
    for t in tokens:
        starts.append(pos)
        pos += len(t) + 1
    return starts


class EntityTagger:
    def __init__(self, categories: Sequence[CategorySpec]) -> None:
        names = [c.name for c in categories]
        if len(set(names)) != len(names):
            raise ValueError(f"duplicate category names: {names}")
        self.categories = tuple(categories)

    @classmethod
    def from_entities(
        cls,
        entities: Iterable[EntityCategory],
        resolve: Callable[[str], Path],
        *,
        date_order: DateOrder = "mdy",
    ) -> EntityTagger:
        """Build from profile entity categories; `resolve` maps lexicon paths to files."""
        specs = []
        for e in entities:
            if e.kind is EntityKind.LEXICON:
                assert e.lexicon_path is not None
                raw_terms = read_lexicon(resolve(e.lexicon_path))
                terms = {tuple(normalize(t, date_order=date_order).split()) for t in raw_terms} - {
                    ()
                }
                specs.append(CategorySpec(e.name, e.kind, terms=tuple(sorted(terms))))
            elif e.kind is EntityKind.REGEX:
                assert e.pattern is not None
                specs.append(CategorySpec(e.name, e.kind, pattern=re.compile(e.pattern)))
            else:
                assert e.builtin is not None
                pattern = re.compile(
                    f"{_TOKEN_START}(?:{_BUILTIN_PATTERNS[e.builtin]}){_TOKEN_END}"
                )
                specs.append(CategorySpec(e.name, e.kind, builtin=e.builtin, pattern=pattern))
        return cls(specs)

    def tag(self, normalized_ref: str) -> list[EntitySpan]:
        tokens = normalized_ref.split()
        text = " ".join(tokens)
        spans: list[EntitySpan] = []
        for spec in self.categories:
            if spec.kind is EntityKind.LEXICON:
                spans.extend(self._tag_lexicon(spec, tokens))
            else:
                assert spec.pattern is not None
                spans.extend(self._tag_regex(spec, spec.pattern, tokens, text))
        # The generic `number` builtin means "numbers not already part of a more specific
        # entity": drop its spans where they overlap a date, phone, ID, etc.
        generic = {c.name for c in self.categories if c.builtin is Builtin.NUMBER}
        specific = [s for s in spans if s.category not in generic]
        spans = specific + [
            s
            for s in spans
            if s.category in generic
            and not any(o.start < s.end and s.start < o.end for o in specific)
        ]
        return sorted(spans, key=lambda s: (s.start, s.end, s.category))

    @staticmethod
    def _tag_lexicon(spec: CategorySpec, tokens: Sequence[str]) -> list[EntitySpan]:
        terms = set(spec.terms)
        lengths = sorted({len(t) for t in terms}, reverse=True)
        spans, i = [], 0
        while i < len(tokens):
            for n in lengths:
                if tuple(tokens[i : i + n]) in terms:
                    spans.append(EntitySpan(spec.name, i, i + n, " ".join(tokens[i : i + n])))
                    i += n
                    break
            else:
                i += 1
        return spans

    @staticmethod
    def _tag_regex(
        spec: CategorySpec, pattern: re.Pattern[str], tokens: Sequence[str], text: str
    ) -> list[EntitySpan]:
        starts = _token_starts(tokens)
        spans = []
        for m in pattern.finditer(text):
            if m.start() == m.end():
                continue
            # Every token the match overlaps belongs to the span.
            first = max(i for i, s in enumerate(starts) if s <= m.start())
            last = max(i for i, s in enumerate(starts) if s < m.end())
            spans.append(EntitySpan(spec.name, first, last + 1, " ".join(tokens[first : last + 1])))
        return spans


def aligned_hyp_tokens(score: UttScore, start: int, end: int) -> list[str]:
    """Hypothesis tokens the alignment pairs with reference tokens [start, end).

    Substituted and correct tokens map one to one; insertions count only when strictly inside
    the span (an insertion at its edge belongs to the neighbouring words); deletions add nothing.
    """
    out: list[str] = []
    for c in score.alignment:
        if c.op in ("equal", "substitute"):
            for r in range(max(start, c.ref_start), min(end, c.ref_end)):
                out.append(score.hyp_tokens[c.hyp_start + (r - c.ref_start)])
        elif c.op == "insert" and start < c.ref_start < end:
            out.extend(score.hyp_tokens[c.hyp_start : c.hyp_end])
    return out


_RAW_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_DIGIT_SEPARATORS = re.compile(r"(?<=\d)[\s().-]+(?=\d)")


def _canonical_number(s: str) -> str:
    whole, _, frac = s.partition(".")
    return (whole.lstrip("0") or "0") + ("." + frac if frac else "")


def _span_numbers(span_text: str) -> list[str]:
    return [
        _canonical_number(tok if tok != "one" else "1")
        for tok in re.findall(r"\d+(?:\.\d+)?|(?<!\S)one(?!\S)", span_text)
    ]


def is_formatted(span: EntitySpan, builtin: Builtin, raw_hyp: str) -> bool:
    """Whether the raw (unnormalized) hypothesis carries the entity's numbers as digits."""
    raw = re.sub(r"(?<=\d),(?=\d{3})", "", raw_hyp)  # thousands separators
    if builtin is Builtin.PHONE:
        joined = _DIGIT_SEPARATORS.sub("", raw)
        return any(span.text in run for run in re.findall(r"\d+", joined))
    available = {_canonical_number(n) for n in _RAW_NUMBER.findall(raw)}
    wanted = _span_numbers(span.text)
    return bool(wanted) and all(n in available for n in wanted)


def score_entities(
    tagger: EntityTagger,
    score: UttScore,
    *,
    raw_hyp: str | None = None,
) -> list[EntityOutcome]:
    """Tag the normalized reference in `score` and score every entity against the alignment."""
    spans = tagger.tag(" ".join(score.ref_tokens))
    hits = score.ref_token_hits()
    specs = {c.name: c for c in tagger.categories}
    outcomes = []
    for span in spans:
        ref_chars = span.text.replace(" ", "")
        hyp_chars = "".join(aligned_hyp_tokens(score, span.start, span.end))
        spec = specs[span.category]
        formatted = None
        if spec.numeric and raw_hyp is not None:
            assert spec.builtin is not None
            recovered = all(hits[span.start : span.end])
            formatted = recovered and is_formatted(span, spec.builtin, raw_hyp)
        outcomes.append(
            EntityOutcome(
                span=span,
                recovered=all(hits[span.start : span.end]),
                char_errors=Levenshtein.distance(ref_chars, hyp_chars),
                char_total=len(ref_chars),
                formatted=formatted,
            )
        )
    return outcomes


def summarize(outcomes: Iterable[EntityOutcome]) -> dict[str, CategorySummary]:
    """Per-category recall (Wilson CI), pooled character error rate and formatted accuracy."""
    by_cat: dict[str, list[EntityOutcome]] = defaultdict(list)
    for o in outcomes:
        by_cat[o.span.category].append(o)
    out = {}
    for cat, items in sorted(by_cat.items()):
        n = len(items)
        recovered = sum(o.recovered for o in items)
        fmt = [o.formatted for o in items if o.formatted is not None]
        out[cat] = CategorySummary(
            category=cat,
            n=n,
            recovered=recovered,
            recall=wilson_interval(recovered, n),
            char_errors=sum(o.char_errors for o in items),
            char_total=sum(o.char_total for o in items),
            formatted=sum(fmt) if fmt else None,
            formatted_accuracy=wilson_interval(sum(fmt), len(fmt)) if fmt else None,
        )
    return out


def keyterm_false_insertions(
    score: UttScore, keyterms: Iterable[str], *, date_order: DateOrder = "mdy"
) -> dict[str, int]:
    """Per boosted term: hypothesis occurrences not matched by the same words in the reference.

    Keyterm boosting can make a provider hallucinate the boosted words; this counts those.
    An occurrence is genuine when all its tokens align as correct to the reference.
    """
    hyp = score.hyp_tokens
    hyp_hits = score.hyp_token_hits()
    terms = {tuple(normalize(t, date_order=date_order).split()) for t in keyterms} - {()}
    out: dict[str, int] = {}
    for toks in sorted(terms):
        n = len(toks)
        out[" ".join(toks)] = sum(
            1
            for i in range(len(hyp) - n + 1)
            if hyp[i : i + n] == toks and not all(hyp_hits[i : i + n])
        )
    return out
