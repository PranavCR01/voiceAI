import json
from pathlib import Path
from typing import Any

import pytest

from harness.metrics.normalize import NORMALIZER_ID, normalize, strip_markup

CASES: list[dict[str, Any]] = [
    json.loads(line)
    for line in (Path(__file__).parent / "fixtures" / "normalization_cases.jsonl")
    .read_text()
    .splitlines()
    if line.strip()
]


@pytest.mark.parametrize("case", CASES, ids=[c["a"] for c in CASES])
def test_normalization_matches_recorded_output(case: dict[str, Any]) -> None:
    """Pins current behavior so any normalizer change shows up as a fixture diff."""
    assert normalize(case["a"]) == case["a_norm"]
    assert normalize(case["b"]) == case["b_norm"]


@pytest.mark.parametrize("case", CASES, ids=[c["a"] for c in CASES])
def test_notes_agree_with_outputs(case: dict[str, Any]) -> None:
    """A pair is flagged as a known mismatch / real difference exactly when it normalizes apart."""
    flagged = case["note"].startswith("KNOWN MISMATCH") or "NOT equivalent" in case["note"]
    flagged = flagged or "real difference" in case["note"]
    assert flagged == (case["a_norm"] != case["b_norm"])


def test_strip_markup() -> None:
    assert strip_markup("a <UNSURE>b</UNSURE> c <UNIN/> d").split() == ["a", "b", "c", "d"]
    assert strip_markup("x < y and 3 > 2") == "x < y and 3 > 2"


def test_normalizer_id_names_package_and_version() -> None:
    assert NORMALIZER_ID.startswith("whisper-normalizer==")
