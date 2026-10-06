"""Utterance manifest: the one format every dataset, augmentation and provider run shares.

A manifest is a JSONL file with one `Utterance` per line. See `harness/datasets/README.md`.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

UTT_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:-]*$"


class ManifestError(ValueError):
    """A manifest file or utterance list violates the schema."""


class AugmentStep(BaseModel):
    """One deterministic transform applied to the parent utterance's audio."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: str = Field(min_length=1)
    params: dict[str, JsonValue] = Field(default_factory=dict)
    seed: int | None = None


class Utterance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    utt_id: str = Field(pattern=UTT_ID_PATTERN)
    dataset: str = Field(min_length=1)
    subset: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)
    audio_path: str = Field(min_length=1)
    channel: int | None = Field(default=None, ge=0)
    start_s: float | None = Field(default=None, ge=0)
    end_s: float | None = Field(default=None, gt=0)
    ref_text: str
    sample_rate: int = Field(gt=0)
    license: str = Field(min_length=1)
    synthetic: bool = False
    augmentation: list[AugmentStep] = Field(default_factory=list)
    parent_utt_id: str | None = Field(default=None, pattern=UTT_ID_PATTERN)
    exclude_reason: str | None = None

    @model_validator(mode="after")
    def _check(self) -> Utterance:
        path = PurePosixPath(self.audio_path)
        if path.is_absolute() or ".." in path.parts or "\\" in self.audio_path:
            raise ValueError(
                "audio_path must be a relative POSIX path inside the data root: "
                f"{self.audio_path!r}"
            )
        if (self.start_s is None) != (self.end_s is None):
            raise ValueError("start_s and end_s must both be set or both be None")
        if self.start_s is not None and self.end_s is not None and self.end_s <= self.start_s:
            raise ValueError(f"end_s ({self.end_s}) must be > start_s ({self.start_s})")
        if bool(self.augmentation) != (self.parent_utt_id is not None):
            raise ValueError("augmented utterances need parent_utt_id, and only they may have one")
        if self.parent_utt_id == self.utt_id:
            raise ValueError("parent_utt_id must differ from utt_id")
        return self

    def resolve_audio(self, data_root: Path) -> Path:
        return data_root / self.audio_path


def _check_unique(utts: Iterable[Utterance]) -> None:
    dupes = sorted(k for k, n in Counter(u.utt_id for u in utts).items() if n > 1)
    if dupes:
        raise ManifestError(f"duplicate utt_id(s): {', '.join(dupes)}")


def read_manifest(path: Path) -> list[Utterance]:
    utts: list[Utterance] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                utts.append(Utterance.model_validate_json(line))
            except ValidationError as e:
                raise ManifestError(f"{path}:{lineno}: {e}") from e
    _check_unique(utts)
    return utts


def write_manifest(path: Path, utts: Iterable[Utterance]) -> None:
    """Write sorted by utt_id so regenerated manifests diff cleanly."""
    ordered = sorted(utts, key=lambda u: u.utt_id)
    _check_unique(ordered)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for u in ordered:
            f.write(u.model_dump_json() + "\n")
