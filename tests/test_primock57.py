import json
from pathlib import Path

import pytest

from harness.datasets import primock57
from harness.datasets.manifest import Utterance, read_manifest, write_manifest
from harness.metrics.normalize import date_order_for, normalize

FIXTURES = Path(__file__).parent / "fixtures" / "primock57"
ROOT = Path(__file__).resolve().parent.parent


def expected() -> list[Utterance]:
    lines = (FIXTURES / "expected_manifest.jsonl").read_text().splitlines()
    return [Utterance.model_validate(json.loads(line)) for line in lines if line.strip()]


def test_fixture_transcripts_produce_expected_manifest() -> None:
    assert sorted(primock57.load(FIXTURES), key=lambda u: u.utt_id) == expected()


def test_manifest_is_byte_identical_across_runs(tmp_path: Path) -> None:
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write_manifest(a, primock57.load(FIXTURES))
    write_manifest(b, primock57.load(FIXTURES))
    assert a.read_bytes() == b.read_bytes()
    assert [u.utt_id for u in read_manifest(a)] == [u.utt_id for u in expected()]


def test_corrections_are_word_bounded_and_case_insensitive() -> None:
    assert primock57.correct("Paracetemol and LISONOPRIL") == "paracetamol and lisinopril"
    assert primock57.correct("paracetemolx stays") == "paracetemolx stays"


@pytest.mark.parametrize(
    ("text", "duration", "reason"),
    [
        ("fine", 1.0, None),
        ("fine", 0.29, "too_short"),
        ("it was <UNIN/>", 0.1, "unintelligible"),  # tags take precedence over length
        ("<INAUDIBLE_SPEECH/>", 2.0, "inaudible"),
        ("<UNSURE>maybe</UNSURE>", 2.0, None),
    ],
)
def test_exclude_reason(text: str, duration: float, reason: str | None) -> None:
    assert primock57.exclude_reason(text, duration) == reason


def test_rejects_unexpected_file_names(tmp_path: Path) -> None:
    (tmp_path / "transcripts").mkdir()
    bad = tmp_path / "transcripts" / "consultation1.TextGrid"
    bad.write_text((FIXTURES / "transcripts" / "day9_consultation01_doctor.TextGrid").read_text())
    with pytest.raises(ValueError, match="unexpected PriMock57 transcript name"):
        primock57.load(tmp_path)


def test_missing_transcripts_dir(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        primock57.load(tmp_path)


def test_language_drives_date_order() -> None:
    [u] = [u for u in expected() if u.subset == "doctor"]
    assert date_order_for(u.language) == "dmy"
    assert normalize("03/04/1980", date_order=date_order_for(u.language)) == "april 3 1980"


def test_fetch_script_pins_the_same_commit() -> None:
    script = (ROOT / "data" / "fetch_primock57.sh").read_text()
    assert f"COMMIT={primock57.PINNED_COMMIT}" in script


def test_committed_manifest_is_valid_and_consistent() -> None:
    utts = read_manifest(ROOT / "data" / "manifests" / "primock57.jsonl")
    assert len(utts) > 5000
    assert {u.dataset for u in utts} == {"primock57"}
    assert all(u.language == "en-GB" and u.license == "CC-BY-4.0" for u in utts)
    for u in utts:
        if u.ref_text_original is not None:
            assert primock57.correct(u.ref_text_original) == u.ref_text
