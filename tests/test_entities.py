import json
import re
from pathlib import Path
from typing import Any

import pytest

from harness.metrics.entities import (
    CategorySpec,
    EntitySpan,
    EntityTagger,
    aligned_hyp_tokens,
    is_formatted,
    keyterm_false_insertions,
    score_entities,
    summarize,
)
from harness.metrics.normalize import normalize
from harness.metrics.wer import score_utterance
from recommender.profile import Builtin, EntityCategory, EntityKind, load_profile, read_lexicon

ROOT = Path(__file__).resolve().parent.parent
CASES = [
    json.loads(line)
    for line in (ROOT / "tests" / "fixtures" / "entity_cases.jsonl").read_text().splitlines()
    if line.strip()
]


def tagger_for(profile_name: str) -> EntityTagger:
    p = load_profile(ROOT / "configs" / "profiles" / f"{profile_name}.yaml")
    return EntityTagger.from_entities(p.entities, p.resolve_path)


def builtin(name: str, kind: Builtin) -> EntityCategory:
    return EntityCategory(name=name, kind=EntityKind.BUILTIN, builtin=kind)


def tagger(*cats: EntityCategory) -> EntityTagger:
    return EntityTagger.from_entities(cats, lambda p: Path(p))


# --- tagging ------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[c["text"] for c in CASES])
def test_hand_labeled_spans(case: dict[str, Any]) -> None:
    spans = tagger_for(case["profile"]).tag(normalize(case["text"]))
    assert [[s.category, s.text] for s in spans] == case["spans"]


def test_both_profiles_covered_by_fixtures() -> None:
    assert {c["profile"] for c in CASES} == {"healthcare_intake", "utility_billing_support"}


def test_no_domain_terms_in_scoring_code() -> None:
    """The engine is generic; domain vocabulary lives in lexicons and profiles only."""
    source = (ROOT / "harness" / "metrics" / "entities.py").read_text().lower()
    lexicon_dir = ROOT / "data" / "lexicons"
    for lexicon in lexicon_dir.glob("*.txt"):
        for term in read_lexicon(lexicon):
            assert not re.search(rf"\b{re.escape(term)}\b", source), (lexicon.name, term)


def test_lexicon_prefers_longest_match(tmp_path: Path) -> None:
    lex = tmp_path / "terms.txt"
    lex.write_text("late\nlate fee\nfee\n")
    t = EntityTagger.from_entities(
        [EntityCategory(name="term", kind=EntityKind.LEXICON, lexicon_path=str(lex))],
        lambda p: Path(p),
    )
    assert [s.text for s in t.tag("a late fee and a fee")] == ["late fee", "fee"]


def test_regex_category_spans_cover_overlapped_tokens() -> None:
    t = tagger(EntityCategory(name="ref_code", kind=EntityKind.REGEX, pattern=r"ab\d+"))
    assert t.tag("code xab12 now") == [EntitySpan("ref_code", 1, 2, "xab12")]


def test_number_builtin_yields_to_specific_categories() -> None:
    t = tagger(builtin("amount", Builtin.NUMBER), builtin("when", Builtin.DATE))
    spans = t.tag(normalize("pay 45 dollars by june 12"))
    assert [(s.category, s.text) for s in spans] == [("amount", "$45"), ("when", "june 12")]


def test_duplicate_category_names_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        EntityTagger([CategorySpec("x", EntityKind.LEXICON), CategorySpec("x", EntityKind.REGEX)])


# --- scoring --------------------------------------------------------------------


def test_one_substitution_inside_a_multi_token_span_misses_the_entity() -> None:
    t = tagger(builtin("dob", Builtin.DATE))
    score = score_utterance("born march 4 1980", "born march 5 1980")
    [outcome] = score_entities(t, score)
    assert outcome.span.text == "march 4 1980"
    assert outcome.recovered is False
    assert outcome.char_errors == 1


def test_phone_one_wrong_digit_costs_one_character_not_the_whole_number() -> None:
    t = tagger(builtin("phone", Builtin.PHONE))
    score = score_utterance(
        "call 07700 900123", "call oh seven seven double oh nine double oh one two four"
    )
    [o] = score_entities(t, score)
    assert (o.recovered, o.char_errors, o.char_total) == (False, 1, 11)


def test_aligned_hyp_tokens_includes_insertions_strictly_inside_span() -> None:
    score = score_utterance("a b c d", "a b x c d", normalized=True)
    assert aligned_hyp_tokens(score, 1, 3) == ["b", "x", "c"]
    assert aligned_hyp_tokens(score, 2, 4) == ["c", "d"]  # insertion at the edge excluded


def test_deleted_entity_has_full_character_error() -> None:
    t = tagger(builtin("dose", Builtin.DOSAGE))
    [o] = score_entities(t, score_utterance("take 10 mg daily", "take daily"))
    assert (o.recovered, o.char_errors, o.char_total) == (False, 4, 4)


@pytest.mark.parametrize(
    ("ref", "raw_hyp", "category", "kind", "recovered", "formatted"),
    [
        ("take 10 mg", "take 10mg", "dose", Builtin.DOSAGE, True, True),
        ("take 10 mg", "take ten milligrams", "dose", Builtin.DOSAGE, True, False),
        ("take 1.5 mg", "take 1.5 mg", "dose", Builtin.DOSAGE, True, True),
        ("born march 4 1980", "born March 4th, 1980", "dob", Builtin.DATE, True, True),
        (
            "born march 4 1980",
            "born march fourth nineteen eighty",
            "dob",
            Builtin.DATE,
            True,
            False,
        ),
        ("born march 4 1980", "born 03/04/1980", "dob", Builtin.DATE, True, True),
        ("call (555) 123-4567", "call (555) 123-4567", "phone", Builtin.PHONE, True, True),
        ("call 07700 900123", "call 07700 900123", "phone", Builtin.PHONE, True, True),
        (
            "call 07700 900123",
            "call oh seven seven double oh nine double oh one two three",
            "phone",
            Builtin.PHONE,
            True,
            False,
        ),
        ("owe $1,250", "owe $1,250", "amount", Builtin.NUMBER, True, True),
        ("take 10 mg", "take 12 mg", "dose", Builtin.DOSAGE, False, False),
    ],
)
def test_formatted_accuracy(
    ref: str, raw_hyp: str, category: str, kind: Builtin, recovered: bool, formatted: bool
) -> None:
    t = tagger(builtin(category, kind))
    [o] = score_entities(t, score_utterance(ref, raw_hyp), raw_hyp=raw_hyp)
    assert (o.recovered, o.formatted) == (recovered, formatted)


def test_formatted_is_none_for_lexicon_categories_and_without_raw_hyp(tmp_path: Path) -> None:
    lex = tmp_path / "t.txt"
    lex.write_text("autopay\n")
    t = EntityTagger.from_entities(
        [
            EntityCategory(name="term", kind=EntityKind.LEXICON, lexicon_path=str(lex)),
            builtin("amount", Builtin.NUMBER),
        ],
        lambda p: Path(p),
    )
    score = score_utterance("autopay of 45", "autopay of 45")
    with_raw = {o.span.category: o.formatted for o in score_entities(t, score, raw_hyp="x 45")}
    assert with_raw == {"term": None, "amount": True}
    assert all(o.formatted is None for o in score_entities(t, score))


def test_is_formatted_requires_digits() -> None:
    span = EntitySpan("dose", 0, 2, "one tablet")
    assert is_formatted(span, Builtin.DOSAGE, "1 tablet")
    assert not is_formatted(span, Builtin.DOSAGE, "one tablet")


def test_summarize_counts_and_intervals() -> None:
    t = tagger(builtin("dose", Builtin.DOSAGE))
    outcomes = [
        *score_entities(t, score_utterance("take 10 mg", "take 10 mg"), raw_hyp="take 10 mg"),
        *score_entities(t, score_utterance("take 20 mg", "take 30 mg"), raw_hyp="take 30 mg"),
        *score_entities(t, score_utterance("take 5 ml", "take five ml"), raw_hyp="take five ml"),
    ]
    s = summarize(outcomes)["dose"]
    assert (s.n, s.recovered, s.formatted) == (3, 2, 1)
    assert s.recall.estimate == pytest.approx(2 / 3)
    assert s.recall.low < 2 / 3 < s.recall.high
    # Characters without spaces: "10mg" + "20mg" + "5ml" = 11; "20mg" -> "30mg" is 1 error.
    assert (s.char_errors, s.char_total) == (1, 11)
    assert s.cer == pytest.approx(1 / 11)


# --- keyterm false insertions ---------------------------------------------------


def test_hallucinated_boosted_term_counts_as_false_insertion() -> None:
    score = score_utterance("i take ibuprofen and rest", "i take ibuprofen and metformin rest")
    counts = keyterm_false_insertions(score, ["Ibuprofen", "Metformin", "Sertraline"])
    assert counts == {"ibuprofen": 0, "metformin": 1, "sertraline": 0}


def test_boosted_term_substituted_for_another_word_is_false() -> None:
    score = score_utterance("he said late", "he said late fee")
    assert keyterm_false_insertions(score, ["late fee"]) == {"late fee": 1}
    score = score_utterance("a late fee", "a late fee")
    assert keyterm_false_insertions(score, ["late fee", "late-fee"]) == {"late fee": 0}
