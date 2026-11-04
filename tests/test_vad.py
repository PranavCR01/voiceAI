"""VAD bounds: exact tests of the pure logic on hand-made probability sequences, sidecar
round-trip/join, and (only when the model has been fetched) the ONNX wrapper's mechanics.

The issue's acceptance test on a synthetic speech-like burst is replaced by these: Silero
barely fires on synthetic signals (peak ~0.74 then ~0.3 on modulated harmonic noise), so a
synthetic test would test the signal generator, not our code. Real-speech validation is in
docs/DECISIONS.md (2026-11-04, VAD bounds).
"""

import os
from pathlib import Path

import numpy as np
import pytest

from harness.audio import AudioClip
from harness.datasets.manifest import Utterance
from harness.vad import (
    MODEL_PATH,
    SileroVad,
    SpeechSpan,
    VadError,
    VadParams,
    join_speech,
    read_speech,
    segments,
    sidecar_path,
    span_for,
    speech_bounds,
    vad_id,
    window_ms,
    write_speech,
)

W = 32.0  # ms per window at 16 kHz
P = VadParams(threshold=0.5, neg_threshold=0.35, min_speech_ms=64, min_silence_ms=96)


def test_window_sizes() -> None:
    assert window_ms(16000) == 32.0 and window_ms(8000) == 32.0
    with pytest.raises(VadError, match="16000 or 8000"):
        window_ms(44100)


def test_hysteresis_enters_at_threshold_and_leaves_below_neg_threshold() -> None:
    probs = [0.1, 0.5, 0.4, 0.36, 0.35, 0.34, 0.1]
    # enters at index 1 (>= 0.5), stays through 0.4/0.36/0.35 (not < 0.35), leaves at index 5
    assert segments(probs, W, P) == [(1, 5)]
    b = speech_bounds(probs, W, P)
    assert b is not None and (b.start_ms, b.end_ms) == (32, 160)


def test_never_reaching_threshold_is_no_speech() -> None:
    assert speech_bounds([0.49] * 50, W, P) is None
    assert speech_bounds([], W, P) is None


def test_short_bursts_dropped_short_gaps_merged() -> None:
    lo, hi = 0.0, 0.9
    click = [hi]  # 32 ms < 64 ms min speech
    gap2 = [lo] * 2  # 64 ms < 96 ms min silence: merged
    gap3 = [lo] * 3  # 96 ms: not merged
    probs = [lo] * 3 + click + [lo] * 5 + [hi] * 4 + gap2 + [hi] * 3 + gap3 + [hi] * 2 + [lo]
    #        0..2      3        4..8      9..12      13,14   15..17    18..20   21,22    23
    assert segments(probs, W, P) == [(9, 18), (21, 23)]
    b = speech_bounds(probs, W, P)
    assert b is not None
    assert (b.start_ms, b.end_ms) == (9 * 32, 23 * 32)  # click at index 3 ignored
    assert b.coverage == pytest.approx((9 + 2) / len(probs))


def test_speech_to_the_last_window_ends_at_clip_end() -> None:
    assert segments([0.0, 0.9, 0.9], W, P) == [(1, 3)]


def test_params_validated() -> None:
    with pytest.raises(ValueError):
        VadParams(threshold=0.3, neg_threshold=0.5)


def _clip(n_samples: int, rate: int = 16000) -> AudioClip:
    return AudioClip(np.zeros(n_samples, dtype=np.int16), rate, "x:1", rate)


def test_span_flags_and_clamping() -> None:
    clip = _clip(16000 * 1 + 100)  # 1006 ms; 32 windows, the last one partial
    probs = [0.0] * 20 + [0.9] * 12  # speech runs into the zero-padded last window
    span = span_for(clip, probs, P)
    assert (span.speech_start_ms, span.speech_end_ms, span.clip_ms) == (640, 1006, 1006)
    assert span.flags == () and span.coverage == pytest.approx(12 / 32)
    quiet = span_for(clip, [0.0] * 32, P)
    assert quiet.flags == ("no_speech",) and quiet.speech_end_ms is None
    sparse = span_for(clip, [0.0] * 29 + [0.9] * 3, P)
    assert sparse.flags == ("low_coverage",)
    assert span.vad_id == vad_id(P) and "silero-vad==6.2.3" in span.vad_id


def _utt(i: int) -> Utterance:
    return Utterance(
        utt_id=f"x:{i}",
        dataset="x",
        subset="s",
        speaker_id="s",
        audio_path=f"x/{i}.wav",
        ref_text="hi",
        sample_rate=16000,
        license="CC0-1.0",
    )


def test_sidecar_round_trip_and_join(tmp_path: Path) -> None:
    spans = [
        SpeechSpan(
            utt_id="x:2",
            speech_start_ms=96,
            speech_end_ms=800,
            clip_ms=1000,
            coverage=0.7,
            vad_id="v",
        ),
        SpeechSpan(utt_id="x:1", clip_ms=500, coverage=0.0, flags=("no_speech",), vad_id="v"),
        SpeechSpan(utt_id="other:9", clip_ms=500, coverage=0.0, vad_id="v"),
    ]
    path = sidecar_path(tmp_path / "m.jsonl")
    assert path.name == "m.speech.jsonl"
    write_speech(path, spans)
    assert path.read_text().splitlines()[0].startswith('{"utt_id":"other:9"')  # sorted
    loaded = read_speech(path)
    assert loaded["x:2"] == spans[0]
    joined = join_speech([_utt(1), _utt(2), _utt(3)], loaded)
    assert sorted(joined.spans) == ["x:1", "x:2"]
    assert joined.missing == ("x:3",)  # reported, never filled with zeros
    assert joined.unknown == ("other:9",)


def test_sidecar_rejects_duplicates(tmp_path: Path) -> None:
    line = SpeechSpan(utt_id="x:1", clip_ms=5, coverage=0.0, vad_id="v").model_dump_json()
    path = tmp_path / "d.speech.jsonl"
    path.write_text(f"{line}\n{line}\n")
    with pytest.raises(VadError, match="duplicate"):
        read_speech(path)


def test_missing_model_says_how_to_fetch(tmp_path: Path) -> None:
    with pytest.raises(VadError, match="fetch_silero_vad"):
        SileroVad(tmp_path / "nope.onnx")


# CI fetches the model (data/fetch_silero_vad.py) and sets REQUIRE_SILERO=1 so this can't
# silently skip there; locally it skips until the model is fetched.
needs_model = pytest.mark.skipif(
    not MODEL_PATH.exists() and not os.environ.get("REQUIRE_SILERO"),
    reason="run `python data/fetch_silero_vad.py`",
)


@needs_model
def test_onnx_wrapper_mechanics() -> None:
    vad = SileroVad()
    probs = vad.probabilities(_clip(16000 + 100))
    assert probs.shape == (32,)  # 31 full windows + 1 zero-padded partial window
    assert float(probs.max()) < 0.5  # digital silence is not speech
    probs8 = vad.probabilities(_clip(8000, rate=8000))
    assert probs8.shape == (32,)  # 256-sample windows at 8 kHz
    again = vad.probabilities(_clip(16000 + 100))
    np.testing.assert_array_equal(probs, again)  # deterministic, state reset per clip
