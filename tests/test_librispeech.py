import json
from pathlib import Path

import pytest

from harness.datasets import librispeech
from harness.datasets.manifest import Utterance

FIX = Path(__file__).parent / "fixtures" / "librispeech"


def test_fixture_produces_expected_manifest() -> None:
    expected = [
        Utterance.model_validate(json.loads(line))
        for line in (FIX / "expected_manifest.jsonl").read_text().splitlines()
        if line.strip()
    ]
    got = librispeech.load(FIX / "LibriSpeech", data_root=FIX)
    assert sorted(got, key=lambda u: u.utt_id) == expected


def test_speakers_come_from_paths() -> None:
    utts = librispeech.load(FIX / "LibriSpeech", data_root=FIX)
    assert {u.speaker_id for u in utts} == {"1089", "121"}


def _tree(tmp_path: Path, name: str, line: str) -> Path:
    d = tmp_path / "LibriSpeech" / "test-clean" / "1089" / "134686"
    d.mkdir(parents=True)
    (d / name).write_text(line + "\n")
    return tmp_path / "LibriSpeech"


def test_rejects_key_that_does_not_match_directory(tmp_path: Path) -> None:
    root = _tree(tmp_path, "1089-134686.trans.txt", "121-121726-0000 WRONG PLACE")
    with pytest.raises(ValueError, match="does not match its directory"):
        librispeech.load(root, data_root=tmp_path)


@pytest.mark.parametrize("line", ["1089-134686-0000", "not-a-key TEXT"])
def test_rejects_malformed_lines(tmp_path: Path, line: str) -> None:
    root = _tree(tmp_path, "1089-134686.trans.txt", line)
    with pytest.raises(ValueError, match="expected"):
        librispeech.load(root, data_root=tmp_path)


def test_missing_subset(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        librispeech.load(tmp_path, data_root=tmp_path)


def test_audio_must_live_under_data_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        librispeech.load(FIX / "LibriSpeech", data_root=tmp_path)
