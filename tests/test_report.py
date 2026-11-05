import json
import os
from pathlib import Path

import pytest

from harness.datasets.manifest import read_manifest
from harness.metrics.wer import score_utterance
from harness.report import build_report, main, render, render_diff
from harness.results import ResultRow, RunMeta, read_runs, write_run
from recommender.profile import load_profile

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "report"
GOLDEN = FIX / "offline_golden.md"
PROFILE = ROOT / "configs" / "profiles" / "healthcare_intake.yaml"


def results_dir(tmp_path: Path) -> Path:
    out = tmp_path / "results"
    for path in sorted((FIX / "runs").glob("*.json")):
        data = json.loads(path.read_text())
        rows = [ResultRow.model_validate(r) for r in data["rows"]]
        write_run(out, RunMeta.model_validate(data["meta"]), rows)
    return out


def run_cli(tmp_path: Path) -> str:
    out = tmp_path / "report.md"
    main(
        [
            "--results",
            str(results_dir(tmp_path)),
            "--manifest",
            "tests/fixtures/report/manifest.jsonl",
            "--profile",
            "configs/profiles/healthcare_intake.yaml",
            "--out",
            str(out),
            "--resamples",
            "2000",
            "--generated-at",
            "2026-10-06 12:00 UTC",
        ]
    )
    return out.read_text()


def test_golden_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regenerate with: UPDATE_GOLDEN=1 uv run pytest tests/test_report.py"""
    monkeypatch.chdir(ROOT)
    text = run_cli(tmp_path)
    if os.environ.get("UPDATE_GOLDEN") == "1":
        GOLDEN.write_text(text)
    assert text == GOLDEN.read_text()


def test_header_states_date_models_and_normalizer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(ROOT)
    text = run_cli(tmp_path)
    assert "**Generated:** 2026-10-06 12:00 UTC" in text
    assert "`fake-a-2026-10`" in text and "`fake-b-v3`" in text
    assert "equiv-v4/dmy" in text and "equiv-v4/mdy" in text  # en-GB real, en-US synthetic
    assert "whisper-normalizer==" in text


def test_synthetic_audio_is_segregated(tmp_path: Path) -> None:
    data = build_report(
        read_manifest(FIX / "manifest.jsonl"),
        read_runs(results_dir(tmp_path)),
        manifest_label="m",
        n_resamples=200,
    )
    real = [g for g in data.groups if not g.synthetic]
    synthetic = [g for g in data.groups if g.synthetic]
    assert [g.title for g in real] == ["All real audio", "doctor (real)", "patient (real)"]
    assert [g.title for g in synthetic] == ["All synthetic audio"]
    assert real[0].configs[0].n_utts == 6 and synthetic[0].configs[0].n_utts == 2


def test_excluded_failed_and_uncovered_utterances(tmp_path: Path) -> None:
    runs = read_runs(results_dir(tmp_path))
    manifest = read_manifest(FIX / "manifest.jsonl")
    data = build_report(manifest, runs, manifest_label="m", n_resamples=200)
    assert data.excluded == {"unintelligible": 1}
    assert data.not_covered == 0
    b = next(c for c in data.groups[0].configs if c.config_id == "fake_b")
    assert b.failed == 1  # the timeout is scored, as an empty transcript

    # Drop one utterance from one run: it is no longer scored for anyone.
    partial = runs[0].model_copy(
        update={"rows": tuple(r for r in runs[0].rows if r.utt_id != "fixture:d2")}
    )
    data = build_report(manifest, [partial, runs[1]], manifest_label="m", n_resamples=200)
    assert data.not_covered == 1
    assert data.groups[0].configs[0].n_utts == 5


def test_entities_scored_per_language_date_order(tmp_path: Path) -> None:
    data = build_report(
        read_manifest(FIX / "manifest.jsonl"),
        read_runs(results_dir(tmp_path)),
        manifest_label="m",
        profile=load_profile(PROFILE),
        n_resamples=200,
    )
    real = {c.config_id: c for c in data.groups[0].configs}
    dose_a, dose_b = real["fake_a"].entities["dosage"], real["fake_b"].entities["dosage"]
    assert (dose_a.recovered, dose_a.formatted) == (2, 2)  # "500mg", "2 puffs"
    assert (dose_b.recovered, dose_b.formatted) == (2, 0)  # spelled out: right but not digits
    synth = {c.config_id: c for c in data.groups[-1].configs}
    assert synth["fake_b"].keyterm_false == 1  # hallucinated "metformin"
    assert synth["fake_b"].entities["phone"].char_errors == 1


def test_no_winner_called_on_too_few_speakers(tmp_path: Path) -> None:
    data = build_report(
        read_manifest(FIX / "manifest.jsonl"),
        read_runs(results_dir(tmp_path)),
        manifest_label="m",
        n_resamples=500,
    )
    [synthetic] = [g for g in data.groups if g.synthetic]
    [pair] = synthetic.pairs
    assert pair.distinguishable  # the bootstrap alone would call it
    assert pair.verdict == "too few speakers (2) to call"


def test_render_diff() -> None:
    score = score_utterance("a b c", "a x c f", normalized=True)
    assert render_diff(score) == "a [b→x] c [+f]"
    assert render_diff(score_utterance("a b", "a", normalized=True)) == "a [-b]"


def test_render_escapes_table_pipes(tmp_path: Path) -> None:
    runs = read_runs(results_dir(tmp_path))
    data = build_report(
        read_manifest(FIX / "manifest.jsonl"), runs, manifest_label="a|b", n_resamples=100
    )
    assert "`a|b`" in render(data)  # header path is in code span; tables escape pipes


def test_hypothesis_date_order_per_config(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from harness.datasets.manifest import Utterance

    utt = Utterance(
        utt_id="x:1",
        dataset="x",
        subset="patient",
        speaker_id="s1",
        audio_path="x/1.wav",
        ref_text="My date of birth is the twentieth of April 1980",
        sample_rate=16000,
        license="CC-BY-4.0",
        language="en-GB",
    )
    hyp = "My date of birth is the 04/20/1980."
    for cid in ("us_fmt", "plain"):
        meta = RunMeta(
            run_id=cid,
            config_id=cid,
            provider="p",
            model_id="m",
            mode="batch",
            created_at=datetime(2026, 11, 4, tzinfo=UTC),
            git_sha="abcdef0",
            manifest="m",
        )
        write_run(tmp_path, meta, [ResultRow(utt_id="x:1", hyp_text=hyp)])
    data = build_report(
        [utt],
        read_runs(tmp_path),
        manifest_label="m",
        profile=load_profile(PROFILE),
        n_resamples=50,
        hyp_date_orders={"us_fmt": "mdy"},
    )
    cfg = {c.config_id: c for c in data.groups[0].configs}
    assert cfg["us_fmt"].entities["date_of_birth"].recovered == 1
    assert cfg["plain"].entities["date_of_birth"].recovered == 0
    assert any(n.endswith("/dmy,hyp-mdy") for n in data.normalizer_ids)
    assert "| mdy |" in render(data) and "| as reference |" in render(data)


def test_empty_on_speech_rate(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from harness.datasets.manifest import Utterance

    def utt(i: int, ref: str) -> Utterance:
        return Utterance(
            utt_id=f"x:{i}",
            dataset="x",
            subset="s",
            speaker_id=f"s{i}",
            audio_path=f"x/{i}.wav",
            ref_text=ref,
            sample_rate=16000,
            license="CC-BY-4.0",
        )

    manifest = [utt(1, "Yes please."), utt(2, "Um."), utt(3, "No thanks."), utt(4, "Okay.")]
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
    rows = [
        ResultRow(utt_id="x:1", hyp_text=""),  # empty on speech
        ResultRow(utt_id="x:2", hyp_text=""),  # filler: correct, and not in the denominator
        ResultRow(utt_id="x:3", hyp_text="No thanks."),
        ResultRow(utt_id="x:4", hyp_text="", error="boom"),  # a failure, counted as failed
    ]
    write_run(tmp_path, meta, rows)
    data = build_report(manifest, read_runs(tmp_path), manifest_label="m", n_resamples=50)
    [c] = data.groups[0].configs
    assert (c.empty_on_speech, c.n_speech, c.failed) == (1, 2, 1)
    assert c.empty_on_speech_rate is not None and c.empty_on_speech_rate.estimate == 0.5
