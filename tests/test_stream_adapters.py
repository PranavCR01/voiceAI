"""Replay tests for the streaming adapters (#18): recorded message sequences through each adapter's
message handler, with our finalize/close at the recorded points. Fixtures:
tests/fixtures/streaming/ (live captures where the host was reachable; see each file's `source`)."""

import base64
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import pytest

from harness.providers.assemblyai_stream import AssemblyAIStream
from harness.providers.deepgram_stream import DeepgramStream
from harness.providers.elevenlabs_stream import ElevenLabsStream
from harness.providers.registry import ProviderConfig, load_registry
from harness.providers.stream_runner import build_protocol, split_settings
from harness.streaming.session import Mapped
from harness.streaming.trace import EventKind

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "streaming"


def config(provider: str, model: str, **settings: Any) -> ProviderConfig:
    return ProviderConfig.model_validate(
        {
            "config_id": f"{provider}_s",
            "provider": provider,
            "model_id": model,
            "mode": "streaming",
            "settings": settings,
            "env_key": "K",
            "pricing": {
                "amount": 1,
                "unit": "hour",
                "billing_basis": "audio_duration",
                "source": "t",
                "as_of": "2026-11-05",
            },
        }
    )


def protocol_for(name: str, model: str | None = None) -> Any:
    if name.startswith("deepgram_flux"):
        return DeepgramStream(config("deepgram", "flux-general-en"), "K", {}, None, "pcm16")
    if name.startswith("deepgram_nova3"):
        return DeepgramStream(config("deepgram", "nova-3"), "K", {}, None, "pcm16")
    if name.startswith("assemblyai"):
        return AssemblyAIStream(
            config("assemblyai", model or "universal-3-6-pro"), "K", {}, None, "pcm16"
        )
    return ElevenLabsStream(config("elevenlabs", "scribe_v2_realtime"), "K", {}, None, "pcm16")


def replay_fixture(path: Path) -> list[tuple[list[Mapped], dict[str, Any]]]:
    doc = json.loads(path.read_text())
    p = protocol_for(path.name, doc.get("model_id"))
    p.reset()
    out = []
    for step in doc["steps"]:
        if "send" in step:
            p.finalize_frame() if step["send"] == "finalize" else p.close_frames()
            continue
        msg = json.dumps(step["recv"])
        mapped = p.handle(msg) or [Mapped(EventKind.INFO)]
        assert [m.kind.value for m in mapped] == step["expect"], (path.name, step["recv"])
        assert p.is_terminal(msg) == step.get("terminal", p.is_terminal(msg))
        out.append((mapped, step))
    return out


FIXTURES = sorted(FIX.glob("*.json"))


@pytest.mark.parametrize("path", FIXTURES, ids=[p.stem for p in FIXTURES])
def test_replay_produces_the_recorded_events(path: Path) -> None:
    out = replay_fixture(path)
    finals = [m for ms, _ in out for m in ms if m.kind is EventKind.FINAL and m.fields.get("text")]
    assert finals, "every fixture has a non-empty final"
    words = finals[0].fields["words"]
    assert words, "every provider here returns word timings on finals"
    assert all(0 <= w["start_ms"] <= w["end_ms"] < 10_000 for w in words)  # audio time, in ms


def test_both_modes_covered_for_every_provider() -> None:
    stems = {p.stem for p in FIXTURES}
    for provider in ("deepgram_nova3", "deepgram_flux", "assemblyai", "elevenlabs_scribe_rt"):
        assert {f"{provider}.natural", f"{provider}.forced"} <= stems


def test_word_timings_are_converted_to_audio_ms() -> None:
    [(nova, _)] = [
        x
        for x in replay_fixture(FIX / "deepgram_nova3.natural.json")
        if x[0][0].kind is EventKind.FINAL
    ][:1]
    assert nova[0].fields["words"][0]["start_ms"] == pytest.approx(160)  # 0.16 s in the capture
    aai = replay_fixture(FIX / "assemblyai.natural.json")
    final = next(m for ms, _ in aai for m in ms if m.kind is EventKind.FINAL)
    assert final.fields["words"][-1] == {"text": "Sonny.", "start_ms": 3016.0, "end_ms": 4155.0}


def test_flux_manual_end_of_turn_is_not_an_endpoint() -> None:
    forced = [m.kind for ms, _ in replay_fixture(FIX / "deepgram_flux.forced.json") for m in ms]
    natural = [m.kind for ms, _ in replay_fixture(FIX / "deepgram_flux.natural.json") for m in ms]
    assert EventKind.ENDPOINT not in forced and EventKind.FINAL in forced
    assert EventKind.ENDPOINT in natural


def test_scribe_replies_to_our_commits_are_not_endpoints() -> None:
    forced = [
        m.kind for ms, _ in replay_fixture(FIX / "elevenlabs_scribe_rt.forced.json") for m in ms
    ]
    natural = [
        m.kind for ms, _ in replay_fixture(FIX / "elevenlabs_scribe_rt.natural.json") for m in ms
    ]
    assert EventKind.ENDPOINT not in forced
    assert natural.count(EventKind.ENDPOINT) == 1  # its own VAD commit, before our closing commit


def test_assemblyai_unformatted_models_finalize_on_the_first_end_of_turn() -> None:
    p = AssemblyAIStream(
        config("assemblyai", "universal-streaming-english"), "K", {}, None, "pcm16"
    )
    p.reset()
    eot = {
        "type": "Turn",
        "turn_order": 0,
        "end_of_turn": True,
        "turn_is_formatted": False,
        "transcript": "my name is sonny",
        "words": [{"text": "my", "start": 10, "end": 90}],
    }
    assert [m.kind for m in p.handle(json.dumps(eot))] == [EventKind.FINAL, EventKind.ENDPOINT]
    assert p.handle(json.dumps(eot | {"turn_is_formatted": True})) == []  # no second final


# --- requests ---------------------------------------------------------------------------------


def query(url: str) -> dict[str, list[str]]:
    q: dict[str, list[str]] = {}
    for k, v in parse_qsl(urlsplit(url).query):
        q.setdefault(k, []).append(v)
    return q


def test_deepgram_urls_and_frames() -> None:
    nova = DeepgramStream(
        config("deepgram", "nova-3"),
        "KEY",
        {"endpointing": 300, "interim_results": True, "keyterms": ["ventolin"]},
        None,
        "mulaw",
    )
    u = nova.url()
    assert u.startswith("wss://api.deepgram.com/v1/listen?")
    assert query(u) == {
        "model": ["nova-3"],
        "encoding": ["mulaw"],
        "sample_rate": ["8000"],
        "endpointing": ["300"],
        "interim_results": ["true"],
        "keyterm": ["ventolin"],
    }
    assert nova.headers() == {"Authorization": "Token KEY"}
    assert nova.finalize_frame() == '{"type": "Finalize"}' and nova.close_frames() == [
        '{"type": "CloseStream"}'
    ]
    flux = DeepgramStream(
        config("deepgram", "flux-general-en"), "KEY", {"eot_threshold": 0.8}, None, "pcm16"
    )
    assert flux.url().startswith(
        "wss://api.deepgram.com/v2/listen?model=flux-general-en&encoding=linear16"
    )
    assert [json.loads(f)["type"] for f in flux.close_frames()] == ["ForceEndTurn", "CloseStream"]
    with pytest.raises(ValueError, match="unsupported settings"):
        DeepgramStream(
            config("deepgram", "flux-general-en"), "K", {"endpointing": 300}, None, "pcm16"
        )
    hosted = config("deepgram", "nova-3").model_copy(update={"base_url": "https://dg.example.com"})
    assert (
        DeepgramStream(hosted, "K", {}, None, "pcm16")
        .url()
        .startswith("wss://dg.example.com/v1/listen")
    )


def test_assemblyai_url_and_keyterms() -> None:
    p = AssemblyAIStream(
        config("assemblyai", "universal-3-6-pro"),
        "KEY",
        {"min_turn_silence": 160, "keyterms": ["Dr. Smith"]},
        None,
        "pcm16",
    )
    assert query(p.url()) == {
        "speech_model": ["universal-3-6-pro"],
        "encoding": ["pcm_s16le"],
        "sample_rate": ["16000"],
        "min_turn_silence": ["160"],
        "keyterms_prompt": ['["Dr. Smith"]'],
    }
    assert p.headers() == {"Authorization": "KEY"}
    with pytest.raises(ValueError, match="keyterms"):
        AssemblyAIStream(config("assemblyai", "u"), "K", {"keyterms": ["x" * 51]}, None, "pcm16")


def test_elevenlabs_url_and_base64_frames() -> None:
    p = ElevenLabsStream(config("elevenlabs", "scribe_v2_realtime"), "KEY", {}, None, "mulaw")
    q = query(p.url())
    assert q["audio_format"] == ["ulaw_8000"] and q["include_timestamps"] == ["true"]
    assert q["commit_strategy"] == ["vad"]
    frame = json.loads(p.audio_frame(b"\x01\x02"))
    assert frame == {
        "message_type": "input_audio_chunk",
        "audio_base_64": base64.b64encode(b"\x01\x02").decode(),
        "commit": False,
        "sample_rate": 8000,
    }
    assert json.loads(p.finalize_frame() or "")["commit"] is True
    with pytest.raises(ValueError, match="keyterms"):
        ElevenLabsStream(
            config("elevenlabs", "scribe_v2_realtime"), "K", {"keyterms": ["x" * 21]}, None, "pcm16"
        )


def test_every_registry_streaming_config_builds() -> None:
    for cfg in load_registry(ROOT / "configs" / "providers.yaml").configs:
        if cfg.mode.value == "streaming":
            s, _ = split_settings(cfg.settings)
            p = build_protocol(cfg, "K", None)
            assert p.url().startswith("wss://") and p.encoding == s.encoding
