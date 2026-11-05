import random
from pathlib import Path
from typing import Any

import pytest

from harness.datasets.manifest import Utterance, read_manifest
from harness.datasets.sample import SampleSpec, ids_digest, sample_record, sample_utterances
from harness.vad import SpeechSpan, read_speech

PRIMOCK = Path("data/manifests/primock57.jsonl")


def utt(spk: str, i: int, subset: str = "patient", excluded: bool = False) -> Utterance:
    return Utterance(
        utt_id=f"d:{spk}:{i:04d}",
        dataset="d",
        subset=subset,
        speaker_id=spk,
        audio_path=f"{spk}.wav",
        start_s=float(i),
        end_s=i + 0.5,
        ref_text="x",
        sample_rate=16000,
        license="CC0-1.0",
        exclude_reason="inaudible" if excluded else None,
    )


def span(u: Utterance, end: float | None = 400) -> SpeechSpan:
    return SpeechSpan(
        utt_id=u.utt_id, speech_start_ms=0, speech_end_ms=end, clip_ms=500, coverage=0.8, vad_id="t"
    )


def manifest() -> list[Utterance]:
    return [utt(s, i) for s in ("a", "b", "c") for i in range(10)] + [
        utt("doc", i, subset="doctor") for i in range(10)
    ]


def test_per_speaker_cap_subset_and_manifest_order() -> None:
    m = manifest()
    got = sample_utterances(m, SampleSpec(subset="patient", per_speaker=3, seed=0))
    assert len(got) == 9
    assert {u.speaker_id for u in got} == {"a", "b", "c"}
    assert [u.utt_id for u in got] == sorted(u.utt_id for u in got)  # manifest order kept


def test_deterministic_and_order_independent() -> None:
    m = manifest()
    spec = SampleSpec(subset="patient", per_speaker=3, seed=0)
    shuffled = m[:]
    random.Random(1).shuffle(shuffled)
    a = {u.utt_id for u in sample_utterances(m, spec)}
    assert a == {u.utt_id for u in sample_utterances(shuffled, spec)}
    other_seed = {u.utt_id for u in sample_utterances(m, spec.model_copy(update={"seed": 1}))}
    assert other_seed != a


def test_adding_utterances_for_one_speaker_keeps_other_speakers_picks() -> None:
    m = manifest()
    spec = SampleSpec(per_speaker=3)
    before = {u.utt_id for u in sample_utterances(m, spec) if u.speaker_id != "a"}
    grown = m + [utt("a", i) for i in range(10, 30)]
    after = {u.utt_id for u in sample_utterances(grown, spec) if u.speaker_id != "a"}
    assert before == after


def test_eligibility_excluded_and_missing_speech_end() -> None:
    m = [utt("a", 0), utt("a", 1, excluded=True), utt("a", 2), utt("a", 3)]
    spans = {m[0].utt_id: span(m[0]), m[1].utt_id: span(m[1]), m[2].utt_id: span(m[2], None)}
    got = sample_utterances(m, SampleSpec(per_speaker=5), spans)
    assert [u.utt_id for u in got] == [m[0].utt_id]  # 1 excluded, 2 no end, 3 no span
    with_excl = sample_utterances(m, SampleSpec(per_speaker=5), spans, include_excluded=True)
    assert [u.utt_id for u in with_excl] == [m[0].utt_id, m[1].utt_id]


def test_speakers_with_fewer_than_the_cap_keep_all() -> None:
    m = [utt("a", i) for i in range(2)] + [utt("b", i) for i in range(8)]
    got = sample_utterances(m, SampleSpec(per_speaker=5))
    assert sum(u.speaker_id == "a" for u in got) == 2
    assert sum(u.speaker_id == "b" for u in got) == 5


def test_record_names_spec_counts_and_ids() -> None:
    m = manifest()
    spec = SampleSpec(subset="patient", per_speaker=2, seed=7)
    got = sample_utterances(m, spec)
    rec = sample_record(spec, got, vad_filtered=False)
    assert rec == {
        "subset": "patient",
        "per_speaker": 2,
        "seed": 7,
        "requires_speech_end": False,
        "utterances": 6,
        "speakers": 3,
        "utt_ids_sha256": ids_digest([u.utt_id for u in got]),
    }
    assert ids_digest(["b", "a"]) == ids_digest(["a", "b"])


def test_primock57_patient_sample_is_pinned() -> None:
    """The committed manifest + VAD sidecar give 285 utterances from 57 patients at seed 0.
    If this digest changes, latency runs recorded with --seed 0 no longer match: the manifest or
    the sidecar changed, or the selection rule did. Record that in docs/DECISIONS.md."""
    utts = read_manifest(PRIMOCK)
    spans = read_speech(PRIMOCK.with_name("primock57.speech.jsonl"))
    spec = SampleSpec(subset="patient", per_speaker=5, seed=0)
    got = sample_utterances(utts, spec, spans)
    rec = sample_record(spec, got, vad_filtered=True)
    assert (rec["utterances"], rec["speakers"]) == (285, 57)
    assert rec["utt_ids_sha256"] == PINNED_DIGEST


PINNED_DIGEST = "6242b5573bb1288b07dc873fe5f925d6ee21e25a277bf7f8793cf4867d92da84"


# --- in the stream runner ---------------------------------------------------------------------


def test_stream_run_records_sample_and_refuses_a_different_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import asyncio

    from harness.providers import stream_runner
    from harness.providers.registry import ProviderConfig
    from harness.providers.runner import RunConflictError
    from harness.results import read_run
    from harness.streaming.trace import SessionTrace

    cfg = ProviderConfig.model_validate(
        {
            "config_id": "echo_stream",
            "provider": "echo",
            "model_id": "m",
            "mode": "streaming",
            "env_key": "X",
            "pricing": {
                "amount": 1,
                "unit": "hour",
                "billing_basis": "audio_duration",
                "source": "t",
                "as_of": "2026-11-05",
            },
        }
    )
    sessions: list[str] = []

    async def fake_session(protocol: Any, clip: Any, meta: Any, **kw: Any) -> SessionTrace:
        sessions.append(meta.utt_id)
        return SessionTrace(meta=meta, events=[])

    monkeypatch.setattr(stream_runner, "stream_session", fake_session)
    m = manifest()
    spans = {u.utt_id: span(u) for u in m}
    spec = SampleSpec(subset="patient", per_speaker=2, seed=0)

    def go(sample: SampleSpec | None, limit: int | None = None) -> Any:
        return asyncio.run(
            stream_runner.run_streaming(
                cfg,
                object(),  # type: ignore[arg-type]
                m,
                load=lambda u: None,  # type: ignore[arg-type,return-value]
                spans=spans,
                results_dir=tmp_path,
                manifest_label="t",
                sha="abcdef0",
                sample=sample,
                limit=limit,
            )
        )

    first = go(spec, limit=4)
    assert first.attempted == 4
    second = go(spec)  # resumes: the remaining 2 of the 6 sampled
    assert (second.attempted, second.skipped_existing) == (2, 4)
    expected = [u.utt_id for u in sample_utterances(m, spec, spans)]
    assert sessions == expected
    meta = read_run(tmp_path / "echo-stream").meta
    assert meta.sample == sample_record(spec, sample_utterances(m, spec, spans), vad_filtered=True)
    with pytest.raises(RunConflictError, match="sample"):
        go(spec.model_copy(update={"seed": 1}))
    with pytest.raises(RunConflictError, match="sample"):
        go(None)


def test_cli_sample_args() -> None:
    import argparse

    from harness.providers.stream_runner import add_sample_args, sample_spec

    ap = argparse.ArgumentParser()
    add_sample_args(ap)
    assert sample_spec(ap.parse_args([])) is None
    spec = sample_spec(ap.parse_args(["--subset", "patient", "--per-speaker", "5"]))
    assert spec == SampleSpec(subset="patient", per_speaker=5, seed=0)
