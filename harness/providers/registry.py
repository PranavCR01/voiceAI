"""Provider configuration registry (`configs/providers.yaml`).

One entry per *configuration*: a provider, a pinned model id, a mode, and the settings that
make it distinct (keyterms on/off, endpointing ms, ...). Prices carry their billing basis,
source and date because the basis changes cost per minute more than the headline rate does.
Values copied from research and not yet checked against vendor docs carry `verify: true`.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

_ID = r"^[a-z0-9][a-z0-9_]*$"


class RegistryError(ValueError):
    """The registry file is unreadable or invalid."""


class Mode(StrEnum):
    BATCH = "batch"
    STREAMING = "streaming"


class PriceUnit(StrEnum):
    MINUTE = "minute"
    HOUR = "hour"


class BillingBasis(StrEnum):
    AUDIO_DURATION = "audio_duration"  # billed for audio actually sent
    SESSION_DURATION = "session_duration"  # billed while the session is open, speech or not
    PER_CHANNEL = "per_channel"  # each audio channel billed separately


class BaaStatus(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Pricing(_Strict):
    amount: float | None = Field(default=None, gt=0)  # USD per unit; None only while unverified
    unit: PriceUnit
    billing_basis: BillingBasis
    source: str = Field(min_length=1)
    as_of: date

    def usd_per_minute(self) -> float | None:
        if self.amount is None:
            return None
        return self.amount if self.unit is PriceUnit.MINUTE else self.amount / 60


class Baa(_Strict):
    status: BaaStatus = BaaStatus.UNKNOWN
    source: str | None = None

    @model_validator(mode="after")
    def _sourced(self) -> Baa:
        if self.status is not BaaStatus.UNKNOWN and not self.source:
            raise ValueError("a BAA status of yes/no needs a source")
        return self


class ProviderConfig(_Strict):
    config_id: str = Field(pattern=_ID)
    provider: str = Field(pattern=_ID)
    model_id: str = Field(min_length=1)
    mode: Mode
    settings: dict[str, JsonValue] = Field(default_factory=dict)
    pricing: Pricing
    baa: Baa = Field(default_factory=Baa)
    env_key: str = Field(pattern=r"^[A-Z][A-Z0-9_]*$")
    verify: bool = True  # model id / price / settings not yet checked against vendor docs
    notes: str = ""

    @model_validator(mode="after")
    def _priced_when_verified(self) -> ProviderConfig:
        if not self.verify and self.pricing.amount is None:
            raise ValueError(f"{self.config_id}: a verified config needs a price amount")
        return self


class Registry(_Strict):
    configs: tuple[ProviderConfig, ...]

    @model_validator(mode="after")
    def _unique(self) -> Registry:
        ids = [c.config_id for c in self.configs]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate config_id: {dupes}")
        return self

    def get(self, config_id: str) -> ProviderConfig:
        for c in self.configs:
            if c.config_id == config_id:
                return c
        raise KeyError(
            f"unknown config_id {config_id!r}; known: {[c.config_id for c in self.configs]}"
        )

    def unverified(self) -> list[str]:
        return [c.config_id for c in self.configs if c.verify]


def load_registry(path: Path) -> Registry:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise RegistryError(f"{path}: cannot read registry: {e}") from e
    try:
        return Registry.model_validate(data)
    except ValidationError as e:
        raise RegistryError(f"{path}: {e}") from e
