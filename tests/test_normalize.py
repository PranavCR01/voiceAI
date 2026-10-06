import json
from pathlib import Path
from typing import Any

import pytest

from harness.metrics.normalize import (
    EQUIVALENCE_VERSION,
    WHISPER_ID,
    date_order_for,
    normalize,
    normalizer_id,
    strip_markup,
)

CASES: list[dict[str, Any]] = [
    json.loads(line)
    for line in (Path(__file__).parent / "fixtures" / "normalization_cases.jsonl")
    .read_text(encoding="utf-8")
    .splitlines()
    if line.strip()
]
IDS = [c["a"] for c in CASES]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_matches_recorded_output(case: dict[str, Any]) -> None:
    """Pins both layers so any normalizer change shows up as a fixture diff."""
    assert normalize(case["a"], equivalences=False) == case["a_whisper"]
    assert normalize(case["b"], equivalences=False) == case["b_whisper"]
    assert normalize(case["a"]) == case["a_norm"]
    assert normalize(case["b"]) == case["b_norm"]


@pytest.mark.parametrize("case", CASES, ids=IDS)
def test_notes_agree_with_outputs(case: dict[str, Any]) -> None:
    """Notes are claims about the outputs; keep them honest.

    - A pair is flagged as a mismatch/real difference exactly when it normalizes apart.
    - A pair is labeled EQUIVALENCE exactly when Whisper alone keeps it apart and the
      equivalence layer brings it together.
    """
    note = case["note"]
    flagged = note.startswith("KNOWN MISMATCH") or "NOT equivalent" in note
    flagged = flagged or "real difference" in note
    assert flagged == (case["a_norm"] != case["b_norm"])
    fixed_by_layer = case["a_whisper"] != case["b_whisper"] and case["a_norm"] == case["b_norm"]
    assert note.startswith("EQUIVALENCE") == fixed_by_layer


def test_equivalence_layer_never_separates_what_whisper_equates() -> None:
    for c in CASES:
        if c["a_whisper"] == c["b_whisper"]:
            assert c["a_norm"] == c["b_norm"], c["a"]


@pytest.mark.parametrize(
    ("text", "date_order", "expected"),
    [
        ("03/04/1980", "mdy", "march 4 1980"),
        ("03/04/1980", "dmy", "april 3 1980"),
        ("13/04/1980", "mdy", "13041980"),  # invalid month: not a date, digits joined as an id
        ("13/04/1980", "dmy", "april 13 1980"),
        ("03/04-1980", "mdy", "03041980"),  # mixed separators: not a date
    ],
)
def test_numeric_dates(text: str, date_order: str, expected: str) -> None:
    assert normalize(text, date_order=date_order) == expected  # type: ignore[arg-type]


def test_okay_rule_does_not_touch_words_starting_with_ok() -> None:
    assert normalize("okra and O.K. and OK") == "okra and okay and okay"


def test_strip_markup() -> None:
    assert strip_markup("a <UNSURE>b</UNSURE> c <UNIN/> d").split() == ["a", "b", "c", "d"]
    assert strip_markup("x < y and 3 > 2") == "x < y and 3 > 2"


def test_normalizer_ids() -> None:
    assert WHISPER_ID.startswith("whisper-normalizer==")
    assert normalizer_id(equivalences=False) == WHISPER_ID
    assert normalizer_id() == f"{WHISPER_ID}+equiv-v{EQUIVALENCE_VERSION}/mdy"
    assert normalizer_id(date_order="dmy").endswith("/dmy")


@pytest.mark.parametrize(
    ("language", "order"),
    [
        (None, "mdy"),
        ("en", "mdy"),
        ("en-US", "mdy"),
        ("en-GB", "dmy"),
        ("en-IN", "dmy"),
        ("es-US", "mdy"),
        ("zh-Hant-TW", "dmy"),
    ],
)
def test_date_order_for(language: str | None, order: str) -> None:
    assert date_order_for(language) == order
