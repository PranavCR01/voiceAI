import random
from collections import Counter
from pathlib import Path

import pytest

from harness.datasets import common_voice
from harness.datasets.common_voice import OTHER, UNSPECIFIED, Clip, read_tsv, sample

FIX = Path(__file__).parent / "fixtures" / "common_voice"
RELEASE = "cv-corpus-fixture"


def clips() -> list[Clip]:
    return read_tsv(FIX / "en" / "test.tsv")


def test_read_tsv_skips_empty_sentences_and_normalizes_accents() -> None:
    cs = clips()
    assert len(cs) == 15  # one row has an empty sentence
    assert Counter(c.accent for c in cs) == {
        "united states english": 8,
        "england english": 3,
        "india and south asia (india, pakistan, sri lanka)": 2,
        UNSPECIFIED: 2,  # blank and whitespace-only
    }


def test_older_releases_use_the_accent_column() -> None:
    assert [c.accent for c in read_tsv(FIX / "old" / "test.tsv")] == ["us", UNSPECIFIED]


def test_missing_columns(tmp_path: Path) -> None:
    tsv = tmp_path / "test.tsv"
    tsv.write_text("client_id\tsentence\nx\thello\n")
    with pytest.raises(ValueError, match="missing columns"):
        read_tsv(tsv)


def test_round_robin_spreads_across_accents() -> None:
    chosen = sample(clips(), n=8, seed=0, min_stratum=1)
    assert Counter(c.accent for c in chosen) == Counter({a: 2 for a in {c.accent for c in clips()}})


def test_per_speaker_cap() -> None:
    chosen = sample(clips(), n=100, seed=0, per_speaker_cap=2, min_stratum=1)
    per_speaker = Counter(c.client_id for c in chosen)
    assert max(per_speaker.values()) == 2
    # spk_us1 has 6 clips and spk_uk1 has 3; both stop at 2, so fewer than n come back.
    assert per_speaker["spk_us1"] == 2 and per_speaker["spk_uk1"] == 2
    assert len(chosen) == 10


def test_deterministic_and_order_independent() -> None:
    base = clips()
    shuffled = base[:]
    random.Random(99).shuffle(shuffled)
    assert sample(base, n=6, seed=3, min_stratum=1) == sample(shuffled, n=6, seed=3, min_stratum=1)
    assert sample(base, n=6, seed=3, min_stratum=1) != sample(base, n=6, seed=4, min_stratum=1)


def test_n_larger_than_available_returns_everything_once() -> None:
    chosen = sample(clips(), n=1000, seed=0, min_stratum=1)
    assert len(chosen) == 15 and len({c.path for c in chosen}) == 15


def test_rare_accents_share_one_stratum() -> None:
    # England (3 clips), India (2) and unspecified (2) fall under min_stratum=5 and pool;
    # US English (8) keeps its own stratum. Two strata alternate.
    chosen = sample(clips(), n=6, seed=0, min_stratum=5)
    us = [c for c in chosen if c.accent == "united states english"]
    assert len(us) == 3 and len(chosen) - len(us) == 3


def test_free_text_long_tail_does_not_crowd_out_common_accents() -> None:
    common = [Clip(f"s{i}", f"a{i}.mp3", "x", "common accent") for i in range(50)]
    rare = [Clip(f"r{i}", f"r{i}.mp3", "x", f"one-off accent {i}") for i in range(200)]
    chosen = sample(common + rare, n=40, seed=0, per_speaker_cap=1)
    assert sum(c.accent == "common accent" for c in chosen) == 20
    assert OTHER not in {c.accent for c in chosen}  # pooling changes strata, not labels


@pytest.mark.parametrize(("n", "cap", "min_stratum"), [(0, 10, 5), (5, 0, 5), (5, 10, 0)])
def test_rejects_bad_parameters(n: int, cap: int, min_stratum: int) -> None:
    with pytest.raises(ValueError):
        sample(clips(), n=n, seed=0, per_speaker_cap=cap, min_stratum=min_stratum)


def test_load_builds_manifest_entries() -> None:
    utts = common_voice.load(FIX / "en", data_root=FIX, release=RELEASE, n=4, seed=0, min_stratum=1)
    assert len(utts) == 4
    u = utts[0]
    assert u.utt_id.startswith(f"common_voice:{RELEASE}:common_voice_en_")
    assert u.subset == f"{RELEASE}/test"
    assert u.audio_path.startswith("en/clips/common_voice_en_")
    assert (u.license, u.language, u.sample_rate) == ("CC0-1.0", "en", 48_000)
    assert len({x.speaker_id for x in utts}) == 4
