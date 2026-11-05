from datetime import UTC, datetime
from typing import Any

import pytest

from harness.datasets.manifest import AugmentStep, Utterance
from harness.metrics.degradation import degradation, render
from harness.results import ResultRow, Run, RunMeta


def utt(i: int, spk: int, *, child: bool = False, excluded: bool = False) -> Utterance:
    base: dict[str, Any] = {
        "dataset": "d",
        "subset": "s",
        "speaker_id": f"spk{spk}",
        "sample_rate": 16000,
        "license": "CC0-1.0",
        "ref_text": "the cat sat on mats",
        "language": "en-GB",
    }
    if child:
        return Utterance(
            utt_id=f"d:{i}:noisy",
            parent_utt_id=f"d:{i}",
            audio_path=f"a/{i}.wav",
            augmentation=[AugmentStep(kind="noise", params={"snr_db": 5}, seed=1)],
            **base,
        )
    return Utterance(
        utt_id=f"d:{i}",
        audio_path=f"{i}.wav",
        exclude_reason="unintelligible" if excluded else None,
        **base,
    )


def run(rows: dict[str, str]) -> Run:
    meta = RunMeta(
        run_id="r",
        config_id="cfg",
        provider="p",
        model_id="m",
        mode="batch",
        created_at=datetime(2026, 11, 5, tzinfo=UTC),
        git_sha="abcdef0",
        manifest="m",
    )
    return Run(meta=meta, rows=tuple(ResultRow(utt_id=k, hyp_text=v) for k, v in rows.items()))


def test_paired_degradation_is_augmented_minus_clean_over_shared_utterances() -> None:
    n = 40
    parents = {f"d:{i}": utt(i, i % 20) for i in range(n)}
    parents["d:99"] = utt(99, 0, excluded=True)
    children = [utt(i, i % 20, child=True) for i in range(n)] + [utt(99, 0, child=True)]
    clean = run({f"d:{i}": "the cat sat on mats" for i in range(n)})
    # Every augmented hypothesis loses one word of five: +20 pp. One child has no row.
    aug = run({f"d:{i}:noisy": "the cat sat on" for i in range(n - 1)} | {"d:99:noisy": ""})
    d = degradation(clean, aug, parents, children, n_resamples=500)
    assert d.utterances == n - 1  # the missing row and the excluded parent are not scored
    assert d.speakers == 20
    assert d.clean.estimate == 0.0 and d.augmented.estimate == pytest.approx(0.2)
    assert d.difference.estimate == pytest.approx(0.2)
    assert d.difference.low == pytest.approx(0.2) and d.p_value < 0.01
    out = render("noisy", [d], {"cfg": 1})
    assert "+20.00 pp" in out and "cfg: 1" in out


def test_different_configs_are_refused() -> None:
    a = run({})
    b = Run(meta=a.meta.model_copy(update={"config_id": "other"}), rows=())
    with pytest.raises(ValueError, match="same config"):
        degradation(a, b, {}, [])
