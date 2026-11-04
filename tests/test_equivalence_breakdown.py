from datetime import UTC, datetime
from pathlib import Path

import pytest

from harness.datasets.manifest import Utterance
from harness.metrics.equivalence_breakdown import breakdown, render
from harness.metrics.normalize import RULES, normalize
from harness.results import ResultRow, RunMeta, read_runs, write_run


def _utt(i: int, ref: str) -> Utterance:
    return Utterance(
        utt_id=f"x:{i}",
        dataset="x",
        subset="s",
        speaker_id=f"s{i}",
        audio_path=f"x/{i}.wav",
        ref_text=ref,
        sample_rate=16000,
        license="CC-BY-4.0",
        language="en-GB",
    )


def test_breakdown_attributes_errors_to_rules(tmp_path: Path) -> None:
    manifest = [
        _utt(1, "OK, take 500 milligrams."),
        _utt(2, "Born on the twentieth of April 1980."),
        _utt(3, "No change here."),
    ]
    hyps = ["Okay, take 500 mg.", "Born on the 04/20/1980.", "No change here."]
    meta = RunMeta(
        run_id="r",
        config_id="c",
        provider="p",
        model_id="m",
        mode="batch",
        created_at=datetime(2026, 11, 4, tzinfo=UTC),
        git_sha="abcdef0",
        manifest="m",
    )
    write_run(
        tmp_path,
        meta,
        [ResultRow(utt_id=u.utt_id, hyp_text=h) for u, h in zip(manifest, hyps, strict=True)],
    )
    b = breakdown(manifest, read_runs(tmp_path), hyp_date_orders={"c": "mdy"})
    assert b.wer_full["c"] == 0.0 and b.wer_whisper["c"] > 0
    effect = {e.rule: e for e in b.effects}
    assert set(effect) == set(RULES)
    for rule in ("okay", "units", "numeric_dates"):
        assert effect[rule].utts_helped == 1 and effect[rule].utts_hurt == 0, rule
        assert effect[rule].errors_removed > 0
    assert effect["decimals"].utts_helped == effect["decimals"].utts_hurt == 0
    assert [x.utt_id for x in effect["units"].examples] == ["x:1"]
    text = render(b, label="m")
    assert "| `okay` | c |" in text and "### `units`" in text


def test_unknown_rule_rejected() -> None:
    with pytest.raises(ValueError, match="unknown equivalence rules"):
        normalize("x", disable=frozenset({"nope"}))
