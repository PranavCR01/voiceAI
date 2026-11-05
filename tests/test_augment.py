"""Augmentation (#16) on generated audio: no corpora, no network. Needs ffmpeg (CI installs it)."""

import asyncio
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from pydantic import JsonValue

from harness.audio import AudioClip, load_clip, to_wav_bytes
from harness.augment import codec, noise, reverb
from harness.augment.recipes import (
    AugmentConfig,
    SpeechRegion,
    apply,
    load_config,
    step_seed,
)
from harness.augment.run import augment_manifest, main
from harness.datasets.manifest import Utterance, read_manifest
from harness.providers.base import Transcript
from harness.providers.registry import ProviderConfig
from harness.providers.runner import audio_loader, run_batch
from harness.vad import SpeechSpan

ROOT = Path(__file__).resolve().parent.parent
SR = 16000


def tone(seconds: float, freq: float = 440.0, amp: float = 8000.0) -> np.ndarray:
    t = np.arange(round(seconds * SR)) / SR
    return (amp * np.sin(2 * np.pi * freq * t)).astype(np.int16)


def white(seconds: float, seed: int, amp: float = 3000.0, rate: int = SR) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return (amp * rng.standard_normal(round(seconds * rate))).clip(-32768, 32767).astype(np.int16)


def write_wav(path: Path, samples: np.ndarray, rate: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(to_wav_bytes(AudioClip(samples, rate, "x", rate)))


def speech_with_silence() -> np.ndarray:
    """0.5 s silence, 1 s broadband 'speech', 0.5 s silence: the VAD region matters for SNR."""
    quiet = np.zeros(SR // 2, dtype=np.int16)
    return np.concatenate([quiet, white(1.0, seed=1, amp=6000), quiet])


@pytest.fixture
def data_root(tmp_path: Path) -> Path:
    root = tmp_path / "data"
    write_wav(root / "src" / "a.wav", speech_with_silence())
    write_wav(root / "src" / "b.wav", tone(1.5))
    for i in range(3):  # noise files, each longer than the clips
        write_wav(root / "noise" / f"n{i}.wav", white(6.0, seed=10 + i))
    rir = np.zeros(4000, dtype=np.int16)
    rir[200] = 20000  # direct path after 200 samples of propagation delay
    rir[201:] = (white(3799 / SR, seed=99, amp=2000) * np.exp(-np.arange(3799) / 600)).astype(
        np.int16
    )
    write_wav(root / "rir" / "r0.wav", rir)
    return root


@pytest.fixture
def config() -> AugmentConfig:
    return AugmentConfig.model_validate(
        {
            "sources": {"noise": "noise", "rir": "rir"},
            "recipes": {
                "telephony_mulaw": [{"kind": "resample", "rate": 8000}, {"kind": "mulaw"}],
                "noise_snr10": [{"kind": "noise", "snr_db": 10}],
                "phone_noisy": [
                    {"kind": "noise", "snr_db": 10},
                    {"kind": "resample", "rate": 8000},
                    {"kind": "mulaw"},
                ],
                "reverb": [{"kind": "reverb"}],
                "opus": [{"kind": "opus", "bitrate": "12k"}],
            },
        }
    )


def manifest() -> list[Utterance]:
    common: dict[str, Any] = {
        "dataset": "gen",
        "subset": "s",
        "sample_rate": SR,
        "license": "CC0-1.0",
        "language": "en-GB",
    }
    return [
        Utterance(
            utt_id="gen:a", speaker_id="spk1", audio_path="src/a.wav", ref_text="a", **common
        ),
        Utterance(
            utt_id="gen:b", speaker_id="spk2", audio_path="src/b.wav", ref_text="b", **common
        ),
        Utterance(
            utt_id="gen:x",
            speaker_id="spk2",
            audio_path="src/b.wav",
            ref_text="x",
            exclude_reason="unintelligible",
            **common,
        ),
    ]


SPANS = {
    "gen:a": SpeechSpan(
        utt_id="gen:a",
        speech_start_ms=500,
        speech_end_ms=1500,
        clip_ms=2000,
        coverage=0.5,
        vad_id="test",
    )
}


def run_recipe(root: Path, config: AugmentConfig, recipe: str, seed: int = 0) -> list[Utterance]:
    return augment_manifest(
        manifest(), recipe=recipe, config=config, data_root=root, seed=seed, spans=SPANS
    )


# --- acceptance ------------------------------------------------------------------------------


def test_same_seed_is_byte_identical_and_a_new_seed_moves_the_noise(
    data_root: Path, config: AugmentConfig
) -> None:
    first = run_recipe(data_root, config, "phone_noisy")
    wav = (data_root / first[0].audio_path).read_bytes()
    again = run_recipe(data_root, config, "phone_noisy")
    assert again == first
    assert (data_root / again[0].audio_path).read_bytes() == wav

    other = run_recipe(data_root, config, "phone_noisy", seed=1)
    a, b = first[0].augmentation[0].params, other[0].augmentation[0].params
    assert (a["noise_file"], a["noise_offset_samples"]) != (
        b["noise_file"],
        b["noise_offset_samples"],
    )
    assert (data_root / other[0].audio_path).read_bytes() != wav


def test_mixing_at_10_db_measures_10_db_on_the_speech_region() -> None:
    speech = tone(2.0)
    nz = white(2.0, seed=5)
    region = noise.Region(SR // 2, 3 * SR // 2, "vad")
    mixed = noise.mix(speech, nz, 10.0, region)
    assert mixed.peak_scale == 1.0
    added = mixed.samples.astype(np.float64) - speech
    measured = noise.snr_db(speech[region.start : region.end], added[region.start : region.end])
    assert measured == pytest.approx(10.0, abs=0.1)


def test_snr_uses_the_vad_region_not_the_silence_around_it(
    data_root: Path, config: AugmentConfig
) -> None:
    [a, b] = run_recipe(data_root, config, "noise_snr10")
    pa, pb = a.augmentation[0].params, b.augmentation[0].params
    assert pa["snr_region"] == "vad" and pa["snr_region_s"] == [0.5, 1.5]
    assert pb["snr_region"] == "whole_clip"  # no sidecar span for gen:b
    parent = speech_with_silence().astype(np.float64)
    child = load_clip(a, data_root).samples.astype(np.float64)
    added = child - parent
    on_speech = noise.snr_db(parent[SR // 2 : 3 * SR // 2], added[SR // 2 : 3 * SR // 2])
    assert on_speech == pytest.approx(10.0, abs=0.1)
    # Over the whole clip the same mix reads ~3 dB worse (half the clip is silence).
    assert noise.snr_db(parent, added) < 8.0


def test_mulaw_recipe_is_8k_mono_and_band_limited(data_root: Path, config: AugmentConfig) -> None:
    [a, _] = run_recipe(data_root, config, "telephony_mulaw")
    assert a.sample_rate == 8000 and a.channel is None
    clip = load_clip(a, data_root, sample_rate=8000)
    assert clip.source_sample_rate == 8000
    up, _ = codec.resample(clip.samples, 8000, SR)
    spectrum = np.abs(np.fft.rfft(up.astype(np.float64))) ** 2
    freqs = np.fft.rfftfreq(len(up), 1 / SR)
    # ffmpeg's upsampler (used here only to measure) has a transition band just above 4 kHz that
    # leaks ~0.1%, with or without mu-law; from 4.5 kHz up the energy is ~3e-6 of the total.
    assert spectrum[freqs > 4500].sum() / spectrum.sum() < 1e-4
    assert spectrum[freqs > 4000].sum() / spectrum.sum() < 5e-3
    # The parent is broadband white noise, so the band limit comes from the recipe.
    parent = np.abs(np.fft.rfft(speech_with_silence().astype(np.float64))) ** 2
    assert parent[np.fft.rfftfreq(2 * SR, 1 / SR) > 4100].sum() / parent.sum() > 0.4


def test_child_manifest_validates_and_feeds_the_runner(
    data_root: Path, config: AugmentConfig, tmp_path: Path
) -> None:
    out = tmp_path / "child.jsonl"
    src = tmp_path / "parent.jsonl"
    src.write_text("".join(u.model_dump_json() + "\n" for u in manifest()))
    (tmp_path / "parent.speech.jsonl").write_text(SPANS["gen:a"].model_dump_json() + "\n")
    main(
        [
            "--manifest",
            str(src),
            "--data-root",
            str(data_root),
            "--recipe",
            "phone_noisy",
            "--out",
            str(out),
            "--config",
            str(write_config(tmp_path, config)),
        ]
    )
    children = read_manifest(out)
    assert [c.utt_id for c in children] == [
        "gen:a:phone_noisy",
        "gen:b:phone_noisy",
    ]  # excluded skipped
    for c in children:
        assert c.parent_utt_id == c.utt_id.removesuffix(":phone_noisy")
        assert [s.kind for s in c.augmentation] == ["noise", "resample", "mulaw"]
        assert all(s.seed is not None for s in c.augmentation)
        assert c.ref_text in {"a", "b"} and c.language == "en-GB"

    seen: list[AudioClip] = []

    class Adapter:
        async def transcribe(self, clip: Any, settings: Mapping[str, JsonValue]) -> Transcript:
            seen.append(clip)
            return Transcript(text="ok", raw={})

    cfg = ProviderConfig.model_validate(
        {
            "config_id": "fake",
            "provider": "fake",
            "model_id": "m",
            "mode": "batch",
            "settings": {},
            "env_key": "FAKE",
            "pricing": {
                "amount": 1,
                "unit": "hour",
                "billing_basis": "audio_duration",
                "source": "test",
                "as_of": "2026-11-05",
            },
        }
    )
    summary = asyncio.run(
        run_batch(
            cfg,
            Adapter(),
            children,
            load_clip=audio_loader(data_root),
            results_dir=tmp_path / "results",
            manifest_label="child",
            sha="abcdef0",
        )
    )
    assert (summary.succeeded, summary.failed) == (2, 0)
    assert {c.sample_rate for c in seen} == {SR} and {c.source_sample_rate for c in seen} == {8000}


def write_config(tmp_path: Path, config: AugmentConfig) -> Path:
    path = tmp_path / "augment.yaml"
    path.write_text(json.dumps(config.model_dump(mode="json")))  # JSON is valid YAML
    return path


def test_ffmpeg_args_are_recorded_verbatim_and_reproduce_the_output(
    data_root: Path, config: AugmentConfig
) -> None:
    [a, _] = run_recipe(data_root, config, "telephony_mulaw")
    resample, mulaw = a.augmentation
    assert resample.params["ffmpeg_version"].startswith("ffmpeg version")  # type: ignore[union-attr]
    [enc, dec] = mulaw.params["ffmpeg_args"]  # type: ignore[misc]
    assert "pcm_mulaw" in enc and enc[0] == "ffmpeg"
    # Replaying the recorded commands on the parent reproduces the child exactly.
    [rs] = resample.params["ffmpeg_args"]  # type: ignore[misc]
    pcm = codec.run_ffmpeg(list(rs), speech_with_silence().astype("<i2").tobytes())
    out = codec.run_ffmpeg(list(dec), codec.run_ffmpeg(list(enc), pcm))
    child = load_clip(a, data_root, sample_rate=8000).samples
    assert np.array_equal(np.frombuffer(out, dtype="<i2"), child)


# --- other behaviour ---------------------------------------------------------------------------


def test_reverb_keeps_speech_where_it_was(data_root: Path, config: AugmentConfig) -> None:
    [a, b] = run_recipe(data_root, config, "reverb")
    assert a.augmentation[0].params["direct_index"] == 200
    child = load_clip(a, data_root).samples.astype(np.float64)
    # Energy stays in the speech region (0.5-1.5 s) plus a tail, not shifted by 200 samples.
    head = np.mean(child[: SR // 2 - 50] ** 2)
    body = np.mean(child[SR // 2 : 3 * SR // 2] ** 2)
    assert head < 1e-3 * body
    assert noise.power(child[SR // 2 : 3 * SR // 2]) == pytest.approx(
        noise.power(speech_with_silence()[SR // 2 : 3 * SR // 2]), rel=0.01
    )


def test_reverb_with_a_pure_delay_is_the_identity() -> None:
    rir = np.zeros(300, dtype=np.int16)
    rir[150] = 10000
    s = tone(0.5)
    out = reverb.convolve(s, rir, noise.Region(0, len(s), "whole_clip"))
    assert np.max(np.abs(out.samples.astype(int) - s.astype(int))) <= 1


def test_opus_round_trip_keeps_length(data_root: Path, config: AugmentConfig) -> None:
    [a, _] = run_recipe(data_root, config, "opus")
    child = load_clip(a, data_root).samples
    assert len(child) == len(speech_with_silence())
    assert a.augmentation[0].params["bitrate"] == "12k"


def test_mix_scales_down_instead_of_clipping_and_keeps_the_snr() -> None:
    speech = tone(1.0, amp=30000)
    nz = white(1.0, seed=3, amp=20000)
    region = noise.Region(0, SR, "whole_clip")
    mixed = noise.mix(speech, nz, 0.0, region)
    assert mixed.peak_scale < 1.0
    added = mixed.samples.astype(np.float64) - mixed.peak_scale * speech
    assert noise.snr_db(mixed.peak_scale * speech.astype(np.float64), added) == pytest.approx(
        0.0, abs=0.1
    )


def test_silent_speech_region_is_an_error() -> None:
    with pytest.raises(noise.SilentRegionError):
        noise.mix(
            np.zeros(SR, dtype=np.int16), white(1.0, seed=1), 10.0, noise.Region(0, SR, "vad")
        )


def test_step_seeds_depend_on_utterance_not_order() -> None:
    assert step_seed(0, "a", 0) == step_seed(0, "a", 0)
    assert (
        len(
            {step_seed(0, "a", 0), step_seed(0, "b", 0), step_seed(1, "a", 0), step_seed(0, "a", 1)}
        )
        == 4
    )


def test_short_noise_file_is_tiled() -> None:
    seg, offset = noise.pick_segment(np.arange(5, dtype=np.int16), 12, np.random.default_rng(0))
    assert offset == 0 and list(seg) == [0, 1, 2, 3, 4, 0, 1, 2, 3, 4, 0, 1]


def test_missing_sources_and_unknown_recipe_fail_early(
    tmp_path: Path, config: AugmentConfig
) -> None:
    with pytest.raises(KeyError, match="unknown recipe"):
        augment_manifest(
            manifest(), recipe="nope", config=config, data_root=tmp_path, seed=0, spans={}
        )
    with pytest.raises(FileNotFoundError, match="no noise audio"):
        apply(
            config.recipe("noise_snr10"),
            tone(1.0),
            SR,
            SpeechRegion(0, 1, "whole_clip"),
            utt_id="u",
            run_seed=0,
            data_root=tmp_path,
            sources=config.sources,
        )


def test_committed_recipes_load() -> None:
    cfg = load_config(ROOT / "configs" / "augment.yaml")
    assert {"telephony_mulaw", "opus_12k", "reverb", "phone_noisy_snr10"} <= set(cfg.recipes)
    assert {f"noise_snr{s}" for s in (20, 10, 5, 0)} <= set(cfg.recipes)
