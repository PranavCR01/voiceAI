"""Use-case profile: the recommender's input.

An FDE describes the use case, its constraints per stack layer, the entity categories that
matter, and optionally points at customer audio. Field reference: `configs/profiles/README.md`.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

Rate = Annotated[float, Field(ge=0, le=1)]
PositiveMs = Annotated[float, Field(gt=0)]
# BCP-47-ish: primary language subtag plus optional subtags (en, en-US, zh-Hant-TW).
LANGUAGE_PATTERN = r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$"
ENTITY_NAME_PATTERN = r"^[a-z][a-z0-9_]*$"


class ProfileError(ValueError):
    """A profile file is unreadable, invalid, or references files that don't exist."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Channel(StrEnum):
    TELEPHONY_8K = "telephony_8k"
    WIDEBAND_16K = "wideband_16k"


class Deployment(StrEnum):
    MANAGED = "managed"
    SELF_HOSTED = "self_hosted"
    EITHER = "either"


class EntityKind(StrEnum):
    LEXICON = "lexicon"
    REGEX = "regex"
    BUILTIN = "builtin"


class Builtin(StrEnum):
    NUMBER = "number"
    DATE = "date"
    DOSAGE = "dosage"
    PHONE = "phone"
    DURATION = "duration"


class UseCase(_Strict):
    name: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    channel: Channel
    languages: list[Annotated[str, Field(pattern=LANGUAGE_PATTERN)]] = Field(min_length=1)
    expected_accents: list[str] = Field(default_factory=list)
    avg_call_minutes: float = Field(gt=0)
    agent_talk_ratio: Rate


class StackConstraints(_Strict):
    max_p95_ttfa_ms: PositiveMs | None = None
    max_cost_per_min_usd: float | None = Field(default=None, gt=0)
    min_task_success_rate: Rate | None = None
    require_baa: bool = False
    data_residency: list[str] = Field(default_factory=list)
    deployment: Deployment = Deployment.EITHER
    min_concurrency: int | None = Field(default=None, ge=1)


class SttConstraints(_Strict):
    min_entity_recall: dict[str, Rate] = Field(default_factory=dict)
    max_wer: Rate | None = None


class TurnTakingConstraints(_Strict):
    max_premature_endpoint_rate: Rate | None = None
    max_p95_endpoint_delay_ms: PositiveMs | None = None


class LlmConstraints(_Strict):
    min_check_pass_rate: dict[str, Rate] = Field(default_factory=dict)
    max_p95_ttft_ms: PositiveMs | None = None
    require_tool_calling: bool = False


class TtsConstraints(_Strict):
    max_p95_ttfb_ms: PositiveMs | None = None
    max_roundtrip_wer: Rate | None = None
    min_entity_pronunciation: Rate | None = None
    voice: list[str] = Field(default_factory=list)


class Constraints(_Strict):
    """Every field is optional; absent means unconstrained."""

    stack: StackConstraints = Field(default_factory=StackConstraints)
    stt: SttConstraints = Field(default_factory=SttConstraints)
    turn_taking: TurnTakingConstraints = Field(default_factory=TurnTakingConstraints)
    llm: LlmConstraints = Field(default_factory=LlmConstraints)
    tts: TtsConstraints = Field(default_factory=TtsConstraints)


class EntityCategory(_Strict):
    name: str = Field(pattern=ENTITY_NAME_PATTERN)
    kind: EntityKind
    lexicon_path: str | None = None
    pattern: str | None = None
    builtin: Builtin | None = None

    @model_validator(mode="after")
    def _one_source(self) -> EntityCategory:
        given = {
            EntityKind.LEXICON: self.lexicon_path,
            EntityKind.REGEX: self.pattern,
            EntityKind.BUILTIN: self.builtin,
        }
        field = {
            EntityKind.LEXICON: "lexicon_path",
            EntityKind.REGEX: "pattern",
            EntityKind.BUILTIN: "builtin",
        }
        if given[self.kind] is None:
            raise ValueError(f"entity {self.name!r} has kind {self.kind} but no {field[self.kind]}")
        extra = [field[k] for k, v in given.items() if k != self.kind and v is not None]
        if extra:
            raise ValueError(f"entity {self.name!r} has kind {self.kind} but also sets {extra}")
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as e:
                raise ValueError(f"entity {self.name!r} pattern does not compile: {e}") from e
        return self

    @property
    def signature(self) -> str:
        """What this category measures, independent of what the profile calls it.

        Builtins are identified by their builtin type (a profile's `date_of_birth` and a suite's
        `date` are the same thing); lexicon and regex categories by their name.
        """
        return self.builtin.value if self.builtin is not None else self.name


class AudioSource(_Strict):
    manifest_path: str = Field(min_length=1)


class Profile(_Strict):
    use_case: UseCase
    constraints: Constraints = Field(default_factory=Constraints)
    entities: list[EntityCategory] = Field(default_factory=list)
    keyterms: list[str] | None = None
    conversation_scripts: str | None = None
    audio: AudioSource | None = None
    reference_suite: str | None = None

    _base_dir: Path = PrivateAttr(default_factory=Path.cwd)

    @model_validator(mode="after")
    def _cross_refs(self) -> Profile:
        names = [e.name for e in self.entities]
        dupes = sorted({n for n in names if names.count(n) > 1})
        if dupes:
            raise ValueError(f"duplicate entity names: {dupes}")
        unknown = sorted(set(self.constraints.stt.min_entity_recall) - set(names))
        if unknown:
            raise ValueError(f"min_entity_recall references undefined entities: {unknown}")
        return self

    @property
    def base_dir(self) -> Path:
        return self._base_dir

    def resolve_path(self, path: str) -> Path:
        """Relative paths in a profile are relative to the profile file's directory."""
        p = Path(path)
        return p if p.is_absolute() else self._base_dir / p

    def referenced_paths(self) -> list[tuple[str, str]]:
        """(field, path) for every file the profile points at."""
        refs = [(f"entities.{e.name}.lexicon_path", e.lexicon_path) for e in self.entities]
        refs.append(("conversation_scripts", self.conversation_scripts))
        refs.append(("audio.manifest_path", self.audio.manifest_path if self.audio else None))
        return [(field, path) for field, path in refs if path is not None]

    def keyterm_list(self) -> list[str]:
        """Explicit `keyterms` if given, else every term from the lexicon entities.

        Lexicon files: one term per line, `#` starts a comment line, blanks ignored.
        """
        if self.keyterms is not None:
            return list(self.keyterms)
        terms: set[str] = set()
        for e in self.entities:
            if e.lexicon_path is not None:
                terms.update(read_lexicon(self.resolve_path(e.lexicon_path)))
        return sorted(terms)


def read_lexicon(path: Path) -> list[str]:
    lines = (ln.strip().lower() for ln in path.read_text(encoding="utf-8").splitlines())
    return [ln for ln in lines if ln and not ln.startswith("#")]


def parse_profile(data: Any, base_dir: Path) -> Profile:
    """Validate an already-parsed profile mapping. Does not check referenced files exist."""
    profile = Profile.model_validate(data)
    profile._base_dir = base_dir
    return profile


def load_profile(path: Path) -> Profile:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise ProfileError(f"{path}: cannot read profile: {e}") from e
    try:
        profile = parse_profile(data, path.parent)
    except ValidationError as e:
        raise ProfileError(f"{path}: {e}") from e
    missing = [
        f"{field}={ref}"
        for field, ref in profile.referenced_paths()
        if not profile.resolve_path(ref).is_file()
    ]
    if missing:
        raise ProfileError(f"{path}: referenced files not found: {', '.join(missing)}")
    return profile
