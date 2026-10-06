from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from harness.datasets.manifest import (
    AugmentStep,
    ManifestError,
    Utterance,
    read_manifest,
    write_manifest,
)


def utt(**overrides: Any) -> Utterance:
    fields: dict[str, Any] = {
        "utt_id": "primock57:day1_consultation01:patient:0003",
        "dataset": "primock57",
        "subset": "patient",
        "speaker_id": "day1_consultation01_patient",
        "audio_path": "primock57/audio/day1_consultation01_patient.wav",
        "start_s": 12.5,
        "end_s": 15.25,
        "ref_text": "I take ten milligrams of amlodipine",
        "sample_rate": 16000,
        "license": "CC-BY-4.0",
    }
    fields.update(overrides)
    return Utterance(**fields)


def augmented(**overrides: Any) -> Utterance:
    fields: dict[str, Any] = {
        "utt_id": "primock57:day1_consultation01:patient:0003:mulaw8k",
        "audio_path": "augmented/primock57/day1_consultation01_patient_0003_mulaw8k.wav",
        "start_s": None,
        "end_s": None,
        "sample_rate": 8000,
        "parent_utt_id": "primock57:day1_consultation01:patient:0003",
        "augmentation": [
            AugmentStep(kind="noise", params={"file": "musan/noise-001.wav", "snr_db": 10}, seed=7),
            AugmentStep(kind="codec", params={"codec": "pcm_mulaw", "sample_rate": 8000}),
        ],
    }
    fields.update(overrides)
    return utt(**fields)


def test_round_trip(tmp_path: Path) -> None:
    utts = [
        utt(),
        augmented(),
        utt(utt_id="librispeech:1089-134686-0000", channel=0, synthetic=True),
    ]
    path = tmp_path / "nested" / "m.jsonl"
    write_manifest(path, utts)
    assert sorted(read_manifest(path), key=lambda u: u.utt_id) == sorted(
        utts, key=lambda u: u.utt_id
    )


def test_write_is_sorted_and_byte_stable(tmp_path: Path) -> None:
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    utts = [utt(utt_id="z:1"), utt(utt_id="a:1"), utt(utt_id="m:1")]
    write_manifest(a, utts)
    write_manifest(b, list(reversed(utts)))
    assert [u.utt_id for u in read_manifest(a)] == ["a:1", "m:1", "z:1"]
    assert a.read_bytes() == b.read_bytes()


def test_read_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    path.write_text("\n" + utt().model_dump_json() + "\n\n")
    assert len(read_manifest(path)) == 1


def test_resolve_audio() -> None:
    assert utt().resolve_audio(Path("/data")) == Path(
        "/data/primock57/audio/day1_consultation01_patient.wav"
    )


def test_whole_file_utterance_without_times() -> None:
    u = utt(start_s=None, end_s=None)
    assert u.start_s is None and u.end_s is None


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"end_s": 12.5}, "must be > start_s"),
        ({"end_s": 10.0}, "must be > start_s"),
        ({"end_s": None}, "both be set"),
        ({"start_s": None}, "both be set"),
        ({"start_s": -1.0}, "greater than or equal to 0"),
        ({"audio_path": "/abs/x.wav"}, "relative POSIX path"),
        ({"audio_path": "../x.wav"}, "relative POSIX path"),
        ({"audio_path": "a\\b.wav"}, "relative POSIX path"),
        ({"utt_id": ""}, "should match pattern"),
        ({"utt_id": "has space"}, "should match pattern"),
        ({"sample_rate": 0}, "greater than 0"),
        ({"channel": -1}, "greater than or equal to 0"),
        ({"license": ""}, "at least 1 character"),
        ({"speaker_id": ""}, "at least 1 character"),
        ({"unknown_field": 1}, "Extra inputs are not permitted"),
        ({"parent_utt_id": "x:1"}, "need parent_utt_id"),
    ],
)
def test_invalid_utterance(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        utt(**overrides)


def test_augmented_without_parent() -> None:
    with pytest.raises(ValidationError, match="need parent_utt_id"):
        augmented(parent_utt_id=None)


def test_parent_is_self() -> None:
    with pytest.raises(ValidationError, match="must differ"):
        augmented(parent_utt_id="primock57:day1_consultation01:patient:0003:mulaw8k")


def test_write_rejects_duplicate_ids(tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="duplicate utt_id"):
        write_manifest(tmp_path / "m.jsonl", [utt(), utt(ref_text="other")])


def test_read_rejects_duplicate_ids(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    line = utt().model_dump_json()
    path.write_text(f"{line}\n{line}\n")
    with pytest.raises(ManifestError, match="duplicate utt_id"):
        read_manifest(path)


def test_read_reports_line_number(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    path.write_text(utt().model_dump_json() + "\n" + '{"utt_id": "x:1"}\n')
    with pytest.raises(ManifestError, match=r"m\.jsonl:2:"):
        read_manifest(path)


def test_read_rejects_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "m.jsonl"
    path.write_text("{not json\n")
    with pytest.raises(ManifestError, match=r"m\.jsonl:1:"):
        read_manifest(path)
