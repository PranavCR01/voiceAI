"""Recipe config (`configs/augment.yaml`) and the step pipeline.

Each step gets its own seed, derived from (run seed, parent utt_id, step index) by hashing, so an
utterance's augmentation doesn't depend on processing order, `--limit` or which other utterances
are in the manifest. Every parameter needed to reproduce a step is returned for the manifest.
"""

from __future__ import annotations

import functools
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, cast

import numpy as np
import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue

from harness.audio import Int16Array, _decode_file
from harness.augment import codec, noise, reverb
from harness.datasets.manifest import AugmentStep

AUDIO_SUFFIXES = (".wav", ".flac")


class _Step(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResampleStep(_Step):
    kind: Literal["resample"]
    rate: int = Field(gt=0)


class MulawStep(_Step):
    kind: Literal["mulaw"]


class OpusStep(_Step):
    kind: Literal["opus"]
    bitrate: str = Field(pattern=r"^\d+(\.\d+)?k$")


class NoiseStep(_Step):
    kind: Literal["noise"]
    snr_db: float


class ReverbStep(_Step):
    kind: Literal["reverb"]


Step = Annotated[
    ResampleStep | MulawStep | OpusStep | NoiseStep | ReverbStep, Field(discriminator="kind")
]


class Sources(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    noise: str | None = None  # directory relative to the data root
    rir: str | None = None


class AugmentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    sources: Sources = Sources()
    recipes: dict[Annotated[str, Field(pattern=r"^[a-z0-9_]+$")], list[Step]]

    def recipe(self, name: str) -> list[Step]:
        if name not in self.recipes:
            raise KeyError(f"unknown recipe {name!r}; known: {sorted(self.recipes)}")
        return self.recipes[name]


def load_config(path: Path) -> AugmentConfig:
    return AugmentConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def step_seed(run_seed: int, utt_id: str, index: int) -> int:
    digest = hashlib.sha256(f"{run_seed}:{utt_id}:{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") >> 1  # non-negative int64


@functools.lru_cache(maxsize=8)
def list_sources(data_root: Path, rel_dir: str | None, what: str) -> list[str]:
    """Audio files under `rel_dir`, as sorted POSIX paths relative to the data root."""
    if rel_dir is None:
        raise ValueError(
            f"recipe needs {what} files but configs/augment.yaml sets no sources.{what}"
        )
    base = data_root / rel_dir
    files = sorted(
        p.relative_to(data_root).as_posix()
        for p in base.rglob("*")
        if p.is_file() and p.suffix.lower() in AUDIO_SUFFIXES
    )
    if not files:
        raise FileNotFoundError(f"no {what} audio under {base} (see data/README.md)")
    return files


@functools.lru_cache(maxsize=64)
def _decoded(path: Path, rate: int) -> Int16Array:
    return _decode_file(path, rate, None)


@dataclass(frozen=True)
class SpeechRegion:
    """Where speech is in the parent clip, in seconds; `basis` is "vad" or "whole_clip"."""

    start_s: float
    end_s: float
    basis: str

    def samples(self, rate: int, length: int) -> noise.Region:
        start = min(length - 1, max(0, round(self.start_s * rate)))
        end = max(start + 1, min(length, round(self.end_s * rate)))
        return noise.Region(start, end, self.basis)


@dataclass(frozen=True)
class Augmented:
    samples: Int16Array
    sample_rate: int
    steps: list[AugmentStep]


def apply(
    steps: list[Step],
    samples: Int16Array,
    rate: int,
    region: SpeechRegion,
    *,
    utt_id: str,
    run_seed: int,
    data_root: Path,
    sources: Sources,
) -> Augmented:
    records: list[AugmentStep] = []
    for i, step in enumerate(steps):
        seed = step_seed(run_seed, utt_id, i)
        rng = np.random.default_rng(seed)
        params: dict[str, JsonValue]
        if isinstance(step, ResampleStep):
            samples, args = codec.resample(samples, rate, step.rate)
            params = {"rate_in": rate, "rate_out": step.rate, "ffmpeg_args": cast(JsonValue, args)}
            params["ffmpeg_version"] = codec.ffmpeg_version()
            rate = step.rate
        elif isinstance(step, MulawStep):
            samples, args = codec.mulaw(samples, rate)
            params = {
                "rate": rate,
                "ffmpeg_args": cast(JsonValue, args),
                "ffmpeg_version": codec.ffmpeg_version(),
            }
        elif isinstance(step, OpusStep):
            samples, args = codec.opus(samples, rate, step.bitrate)
            params = {"rate": rate, "bitrate": step.bitrate, "ffmpeg_args": cast(JsonValue, args)}
            params["ffmpeg_version"] = codec.ffmpeg_version()
        elif isinstance(step, NoiseStep):
            files = list_sources(data_root, sources.noise, "noise")
            rel = files[int(rng.integers(0, len(files)))]
            source = _decoded(data_root / rel, rate)
            segment, offset = noise.pick_segment(source, len(samples), rng)
            r = region.samples(rate, len(samples))
            mixed = noise.mix(samples, segment, step.snr_db, r)
            samples = mixed.samples
            params = {
                "snr_db": step.snr_db,
                "noise_file": rel,
                "noise_offset_samples": offset,
                "noise_rate": rate,
                "noise_tiled": len(source) < len(samples),
                "snr_region": r.basis,
                "snr_region_s": [round(r.start / rate, 4), round(r.end / rate, 4)],
                "noise_gain": round(mixed.noise_gain, 8),
                "peak_scale": round(mixed.peak_scale, 8),
            }
        else:  # ReverbStep
            files = list_sources(data_root, sources.rir, "rir")
            rel = files[int(rng.integers(0, len(files)))]
            out = reverb.convolve(
                samples, _decoded(data_root / rel, rate), region.samples(rate, len(samples))
            )
            samples = out.samples
            params = {
                "rir_file": rel,
                "rir_rate": rate,
                "direct_index": out.direct_index,
                "level_scale": round(out.level_scale, 8),
            }
        records.append(AugmentStep(kind=step.kind, params=params, seed=seed))
    return Augmented(samples, rate, records)
