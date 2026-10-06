from pathlib import Path
from typing import Any

import pytest
import yaml

from harness.providers.registry import (
    BillingBasis,
    Mode,
    RegistryError,
    load_registry,
)

ROOT = Path(__file__).resolve().parent.parent


def entry(**overrides: Any) -> dict[str, Any]:
    e: dict[str, Any] = {
        "config_id": "x_batch",
        "provider": "x",
        "model_id": "x-1",
        "mode": "batch",
        "pricing": {
            "amount": 0.006,
            "unit": "minute",
            "billing_basis": "audio_duration",
            "source": "https://example.com/pricing",
            "as_of": "2026-10-06",
        },
        "env_key": "X_API_KEY",
    }
    e.update(overrides)
    return e


def write(tmp_path: Path, *entries: dict[str, Any]) -> Path:
    path = tmp_path / "providers.yaml"
    path.write_text(yaml.safe_dump({"configs": list(entries)}))
    return path


def test_committed_registry_loads_and_flags_unverified() -> None:
    reg = load_registry(ROOT / "configs" / "providers.yaml")
    ids = {c.config_id for c in reg.configs}
    assert {
        "deepgram_nova3_stream",
        "deepgram_flux_stream",
        "assemblyai_universal_stream",
        "elevenlabs_scribe_v2_rt_stream",
    } <= ids
    assert set(reg.unverified()) == ids  # nothing checked against vendor docs yet
    assert (
        reg.get("assemblyai_universal_stream").pricing.billing_basis
        is BillingBasis.SESSION_DURATION
    )
    assert {c.mode for c in reg.configs} == {Mode.BATCH, Mode.STREAMING}


def test_price_per_minute() -> None:
    reg = load_registry(ROOT / "configs" / "providers.yaml")
    assert reg.get("assemblyai_universal_stream").pricing.usd_per_minute() == pytest.approx(0.0025)
    assert reg.get("deepgram_nova3_stream").pricing.usd_per_minute() == pytest.approx(0.0077)
    assert reg.get("assemblyai_batch").pricing.usd_per_minute() is None


def test_get_unknown_config() -> None:
    reg = load_registry(ROOT / "configs" / "providers.yaml")
    with pytest.raises(KeyError, match="unknown config_id"):
        reg.get("nope")


@pytest.mark.parametrize(
    ("entries", "message"),
    [
        ([entry(), entry()], "duplicate config_id"),
        ([entry(pricing={**entry()["pricing"], "billing_basis": "per_word"})], "audio_duration"),
        ([entry(pricing={k: v for k, v in entry()["pricing"].items() if k != "source"})], "source"),
        ([entry(pricing={k: v for k, v in entry()["pricing"].items() if k != "as_of"})], "as_of"),
        ([entry(pricing={**entry()["pricing"], "amount": None}, verify=False)], "needs a price"),
        ([entry(pricing={**entry()["pricing"], "amount": 0})], "greater than 0"),
        ([entry(mode="realtime")], "batch"),
        ([entry(config_id="Bad-Id")], "should match pattern"),
        ([entry(env_key="lowercase")], "should match pattern"),
        ([entry(baa={"status": "yes"})], "needs a source"),
        ([entry(surprise=1)], "Extra inputs"),
    ],
)
def test_validation_errors(tmp_path: Path, entries: list[dict[str, Any]], message: str) -> None:
    with pytest.raises(RegistryError, match=message):
        load_registry(write(tmp_path, *entries))


def test_unreadable(tmp_path: Path) -> None:
    with pytest.raises(RegistryError, match="cannot read"):
        load_registry(tmp_path / "missing.yaml")
