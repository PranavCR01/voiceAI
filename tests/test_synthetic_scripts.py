import json
import random
from pathlib import Path

import pytest

from harness.datasets.manifest import read_manifest
from harness.metrics.normalize import normalize
from harness.synthetic.scripts import (
    Voice,
    check,
    default_voices,
    generate,
    main,
    ordinal_words,
    spoken_digits,
    words,
    write_script,
    year_words,
)
from recommender.profile import load_profile

PROFILES = Path(__file__).resolve().parent.parent / "configs" / "profiles"
HEALTHCARE = load_profile(PROFILES / "healthcare_intake.yaml")
BILLING = load_profile(PROFILES / "utility_billing_support.yaml")
VOICES = [Voice.parse(s) for s in default_voices("en-US")]


def test_number_words() -> None:
    assert [words(n) for n in (0, 13, 40, 75, 100, 250, 1000, 2500)] == [
        "zero",
        "thirteen",
        "forty",
        "seventy five",
        "one hundred",
        "two hundred fifty",
        "one thousand",
        "two thousand five hundred",
    ]
    assert [ordinal_words(n) for n in (1, 2, 3, 9, 12, 20, 21, 29, 30)] == [
        "first",
        "second",
        "third",
        "ninth",
        "twelfth",
        "twentieth",
        "twenty first",
        "twenty ninth",
        "thirtieth",
    ]
    assert [year_words(y) for y in (1982, 1905, 2000, 2005, 1900)] == [
        "nineteen eighty two",
        "nineteen oh five",
        "two thousand",
        "two thousand and five",
        "nineteen hundred",
    ]


def test_spoken_digits_with_double_and_groups() -> None:
    texts = {spoken_digits("07700900123", random.Random(s), groups=(5,)) for s in range(20)}
    assert "oh double seven double oh, nine double oh one two three" in texts
    assert "zero seven seven zero zero, nine zero zero one two three" in texts
    assert {normalize(t) for t in texts} == {"07700900123"}


@pytest.mark.parametrize("profile", [HEALTHCARE, BILLING], ids=["healthcare", "billing"])
def test_same_seed_same_bytes(profile, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    a = write_script(tmp_path / "a.jsonl", generate(profile, name="x", voices=VOICES, seed=7))
    b = write_script(tmp_path / "b.jsonl", generate(profile, name="x", voices=VOICES, seed=7))
    assert (tmp_path / "a.jsonl").read_bytes() == (tmp_path / "b.jsonl").read_bytes()
    assert a.read_bytes() == b.read_bytes()
    write_script(tmp_path / "c.jsonl", generate(profile, name="x", voices=VOICES, seed=8))
    assert (tmp_path / "a.jsonl").read_bytes() != (tmp_path / "c.jsonl").read_bytes()


@pytest.mark.parametrize("profile", [HEALTHCARE, BILLING], ids=["healthcare", "billing"])
def test_tagger_finds_inserted_entities(profile) -> None:  # type: ignore[no-untyped-def]
    script = generate(profile, name="x", voices=VOICES, seed=0, target=250)
    found, misses = check(script, profile)
    total = sum(script.counts.values())
    assert sum(found.values()) / total >= 0.99, misses[:10]
    assert all(script.counts[c] >= 250 for c in script.counts)
    assert set(script.counts) == {e.name for e in profile.entities}


def test_manifest_fields_and_voice_round_robin() -> None:
    script = generate(HEALTHCARE, name="hc", voices=VOICES, seed=0, target=30)
    utts = script.utterances
    assert all(u.synthetic and u.language == "en-US" and u.sample_rate == 16000 for u in utts)
    assert [u.speaker_id for u in utts[:3]] == ["tts_a.voice1", "tts_a.voice2", "tts_a.voice3"]
    assert {u.subset for u in utts} == {"tts_a", "tts_b"}
    assert utts[0].audio_path == "synthetic/hc/tts_a.voice1/0000.wav"
    assert len({u.ref_text for u in utts}) > 0.9 * len(utts)  # no script line per voice copy


def test_disfluency_rate_and_entities_untouched() -> None:
    script = generate(HEALTHCARE, name="x", voices=VOICES, seed=0)
    kinds = [k for k in script.disfluency.values() if k is not None]
    assert 0.25 <= len(kinds) / len(script.utterances) <= 0.35
    assert set(kinds) == {"lead", "mid", "restart"}
    for u in script.utterances:
        for r in script.entities[u.utt_id]:
            assert r.spoken in u.ref_text  # never split by a filler


def test_unsupported_regex_category_is_an_error(tmp_path: Path) -> None:
    from recommender.profile import parse_profile

    (tmp_path / "t.yaml").write_text('templates: ["code {code}"]\n')
    profile = parse_profile(
        {
            "use_case": {
                "name": "x",
                "domain": "y",
                "channel": "telephony_8k",
                "languages": ["en-US"],
                "avg_call_minutes": 3,
                "agent_talk_ratio": 0.5,
            },
            "synthetic_templates": "t.yaml",
            "entities": [{"name": "code", "kind": "regex", "pattern": "[A-Z]{3}-\\d+"}],
        },
        tmp_path,
    )
    with pytest.raises(ValueError, match="no generator for regex"):
        generate(profile, name="x", voices=VOICES)


def test_unknown_placeholder_rejected(tmp_path: Path) -> None:
    from recommender.profile import parse_profile

    (tmp_path / "t.yaml").write_text('templates: ["hi {nope}"]\n')
    data = {
        "use_case": {
            "name": "x",
            "domain": "y",
            "channel": "telephony_8k",
            "languages": ["en-US"],
            "avg_call_minutes": 3,
            "agent_talk_ratio": 0.5,
        },
        "synthetic_templates": "t.yaml",
    }
    with pytest.raises(ValueError, match="unknown placeholders"):
        generate(parse_profile(data, tmp_path), name="x", voices=VOICES)


def test_uk_voice_gets_fictional_uk_numbers_and_dmy_scoring() -> None:
    voices = [Voice.parse("v:a:en-GB")]
    script = generate(HEALTHCARE, name="x", voices=voices, seed=1, target=40)
    phones = [r.expected for e in script.entities.values() for r in e if r.category == "phone"]
    assert phones and all(p.startswith(("07700900", "0207946")) for p in phones)
    found, misses = check(script, HEALTHCARE)
    assert not misses


def test_cli_writes_manifest_and_sidecar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "s.jsonl"
    main(
        ["--profile", str(PROFILES / "healthcare_intake.yaml"), "--out", str(out), "--target", "20"]
    )
    report = json.loads(capsys.readouterr().out)
    assert report["found_rate"] == 1.0 and not report["misses"]
    assert len(read_manifest(out)) == report["utterances"]
    side = [json.loads(line) for line in (tmp_path / "s.entities.jsonl").read_text().splitlines()]
    assert {"utt_id", "disfluency", "entities"} <= set(side[0])
