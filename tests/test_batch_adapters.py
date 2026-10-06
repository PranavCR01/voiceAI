import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest

from harness.audio import AudioClip
from harness.providers.assemblyai_batch import AssemblyAIBatch
from harness.providers.base import PermanentError, RetryableError
from harness.providers.deepgram_batch import DeepgramBatch
from harness.providers.elevenlabs_batch import ElevenLabsBatch
from harness.providers.registry import ProviderConfig, load_registry
from harness.providers.runner import BATCH_ADAPTERS

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures" / "providers"
CLIP = AudioClip(np.zeros(1600, dtype=np.int16), 16000, "a:1", 16000)
Handler = Callable[[httpx.Request], httpx.Response]


def fixture(path: str) -> Any:
    return json.loads((FIX / path).read_text())


def config(provider: str, **settings: Any) -> ProviderConfig:
    return ProviderConfig.model_validate(
        {
            "config_id": f"{provider}_test",
            "provider": provider,
            "model_id": "model-x",
            "mode": "batch",
            "settings": settings,
            "pricing": {
                "amount": 1,
                "unit": "hour",
                "billing_basis": "audio_duration",
                "source": "t",
                "as_of": "2026-10-06",
            },
            "env_key": "X_KEY",
        }
    )


def client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def multipart_fields(request: httpx.Request) -> list[tuple[str, str]]:
    """(name, value) for plain multipart fields, in order; file parts reported as <file>."""
    boundary = request.headers["content-type"].split("boundary=")[1].encode()
    fields = []
    for part in request.content.split(b"--" + boundary)[1:-1]:
        head, _, body = part.partition(b"\r\n\r\n")
        name = head.split(b'name="')[1].split(b'"')[0].decode()
        fields.append((name, "<file>" if b"filename=" in head else body.rstrip(b"\r\n").decode()))
    return fields


# --- Deepgram -------------------------------------------------------------------------


def test_deepgram_request_and_parse() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=fixture("deepgram/success.json"))

    cfg = config("deepgram", smart_format=True, punctuate=False, keyterms="profile")
    adapter = DeepgramBatch(
        cfg, "KEY", keyterms=["paracetamol", "co-codamol"], client=client(handler)
    )
    tr = run(adapter.transcribe(CLIP, cfg.settings))
    assert tr.text == "I take 500 mg of paracetamol."
    assert tr.raw == fixture("deepgram/success.json")
    [req] = seen
    assert (req.method, req.url.host, req.url.path) == ("POST", "api.deepgram.com", "/v1/listen")
    assert req.headers["authorization"] == "Token KEY"
    assert req.url.params.get_list("keyterm") == ["paracetamol", "co-codamol"]
    assert (
        req.url.params["model"],
        req.url.params["smart_format"],
        req.url.params["punctuate"],
    ) == ("model-x", "true", "false")
    assert req.content[:4] == b"RIFF"  # WAV body


def test_deepgram_unexpected_shape_is_permanent() -> None:
    adapter = DeepgramBatch(
        config("deepgram"), "K", client=client(lambda r: httpx.Response(200, json={"results": {}}))
    )
    with pytest.raises(PermanentError, match="unexpected response shape"):
        run(adapter.transcribe(CLIP, {}))


# --- shared error mapping -----------------------------------------------------------------


def _adapters(handler: Handler) -> list[Any]:
    c = client(handler)
    return [
        DeepgramBatch(config("deepgram"), "K", client=c),
        AssemblyAIBatch(config("assemblyai"), "K", client=c),
        ElevenLabsBatch(config("elevenlabs"), "K", client=c),
    ]


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (httpx.Response(401, json=fixture("deepgram/error_401.json")), PermanentError),
        (httpx.Response(400, text="bad request"), PermanentError),
        (httpx.Response(429, text="slow down"), RetryableError),
        (httpx.Response(503, text="unavailable"), RetryableError),
        (httpx.Response(200, text="{not json"), PermanentError),
    ],
)
def test_error_mapping(response: httpx.Response, error: type[Exception]) -> None:
    for adapter in _adapters(lambda r: response):
        with pytest.raises(error):
            run(adapter.transcribe(CLIP, {}))


def test_transport_failures_are_retryable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("timed out", request=request)

    for adapter in _adapters(handler):
        with pytest.raises(RetryableError, match="ConnectTimeout"):
            run(adapter.transcribe(CLIP, {}))


# --- settings ------------------------------------------------------------------------------


@pytest.mark.parametrize("cls", [DeepgramBatch, AssemblyAIBatch, ElevenLabsBatch])
def test_unknown_settings_rejected(cls: Any) -> None:
    with pytest.raises(ValueError, match="unsupported settings"):
        cls(config("x", endpointing_typo=300), "K")


@pytest.mark.parametrize("cls", [DeepgramBatch, AssemblyAIBatch, ElevenLabsBatch])
def test_profile_keyterms_require_a_profile(cls: Any) -> None:
    with pytest.raises(ValueError, match="needs --profile"):
        cls(config("x", keyterms="profile"), "K")
    with pytest.raises(ValueError, match="list of strings"):
        cls(config("x", keyterms=5), "K")
    assert cls(config("x", keyterms=["a", "b"]), "K").keyterms == ["a", "b"]


# --- AssemblyAI -------------------------------------------------------------------------


def _assemblyai(
    statuses: list[str], **kw: Any
) -> tuple[AssemblyAIBatch, list[httpx.Request], list[float]]:
    seen: list[httpx.Request] = []
    waits: list[float] = []
    polls = iter(statuses)

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/v2/upload":
            return httpx.Response(200, json=fixture("assemblyai/upload.json"))
        if request.method == "POST":
            return httpx.Response(200, json=fixture("assemblyai/transcript_queued.json"))
        return httpx.Response(200, json=fixture(f"assemblyai/transcript_{next(polls)}.json"))

    async def sleep(s: float) -> None:
        waits.append(s)

    cfg = config("assemblyai", format_text=True, keyterms=["paracetamol"])
    adapter = AssemblyAIBatch(
        cfg, "KEY", client=client(handler), sleep=sleep, poll_interval_s=2, **kw
    )
    return adapter, seen, waits


def test_assemblyai_upload_create_poll() -> None:
    adapter, seen, waits = _assemblyai(["queued", "processing", "completed"])
    tr = run(adapter.transcribe(CLIP, {"format_text": True}))
    assert tr.text == "I take 500 mg of paracetamol."
    upload, create, *polls = seen
    assert upload.headers["authorization"] == "KEY" and upload.content[:4] == b"RIFF"
    assert json.loads(create.content) == {
        "audio_url": "https://cdn.assemblyai.com/upload/fixture",
        "speech_model": "model-x",
        "format_text": True,
        "keyterms_prompt": ["paracetamol"],
    }
    assert [p.url.path for p in polls] == ["/v2/transcript/fixture-transcript"] * 3
    assert waits == [2, 2]


def test_assemblyai_transcript_error_is_permanent() -> None:
    adapter, _, _ = _assemblyai(["processing", "error"])
    with pytest.raises(PermanentError, match="could not be decoded"):
        run(adapter.transcribe(CLIP, {}))


def test_assemblyai_poll_timeout_is_retryable() -> None:
    adapter, _, waits = _assemblyai(["processing"] * 10, poll_timeout_s=5)
    with pytest.raises(RetryableError, match="not done after"):
        run(adapter.transcribe(CLIP, {}))
    assert sum(waits) >= 5


# --- ElevenLabs -------------------------------------------------------------------------


def test_elevenlabs_multipart_request_and_parse() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=fixture("elevenlabs/success.json"))

    cfg = config("elevenlabs", language_code="en", keyterms=["paracetamol", "ventolin"])
    tr = run(ElevenLabsBatch(cfg, "KEY", client=client(handler)).transcribe(CLIP, cfg.settings))
    assert tr.text == "I take 500 mg of paracetamol."
    [req] = seen
    assert req.headers["xi-api-key"] == "KEY" and req.url.path == "/v1/speech-to-text"
    assert multipart_fields(req) == [
        ("model_id", "model-x"),
        ("tag_audio_events", "false"),
        ("language_code", "en"),
        ("keyterms", "paracetamol"),
        ("keyterms", "ventolin"),
        ("file", "<file>"),
    ]


def test_elevenlabs_missing_text_is_permanent() -> None:
    adapter = ElevenLabsBatch(
        config("elevenlabs"), "K", client=client(lambda r: httpx.Response(200, json={"words": []}))
    )
    with pytest.raises(PermanentError, match="no 'text'"):
        run(adapter.transcribe(CLIP, {}))


# --- wiring ---------------------------------------------------------------------------------


def test_every_registry_batch_config_has_an_adapter_that_accepts_its_settings() -> None:
    for cfg in load_registry(ROOT / "configs" / "providers.yaml").configs:
        if cfg.mode.value == "batch":
            assert cfg.provider in BATCH_ADAPTERS
            BATCH_ADAPTERS[cfg.provider](cfg, "KEY", ["paracetamol"])  # settings validate


def test_end_to_end_runner_audio_adapter(tmp_path: Path) -> None:
    import wave

    from harness.datasets.manifest import Utterance
    from harness.providers.runner import audio_loader, run_batch
    from harness.results import read_run

    (tmp_path / "data").mkdir()
    with wave.open(str(tmp_path / "data" / "u.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(np.zeros(8000, dtype="<i2").tobytes())
    utt = Utterance(
        utt_id="e2e:1",
        dataset="e2e",
        subset="s",
        speaker_id="x",
        audio_path="u.wav",
        ref_text="I take 500 mg of paracetamol.",
        sample_rate=16000,
        license="CC0-1.0",
    )
    bodies: list[bytes] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(request.content)
        return httpx.Response(200, json=fixture("deepgram/success.json"))

    cfg = config("deepgram", smart_format=True)
    summary = asyncio.run(
        run_batch(
            cfg,
            DeepgramBatch(cfg, "K", client=client(handler)),
            [utt],
            load_clip=audio_loader(tmp_path / "data"),
            results_dir=tmp_path / "results",
            manifest_label="e2e",
            sha="abcdef0",
        )
    )
    [row] = read_run(summary.run_dir).rows
    assert row.hyp_text == "I take 500 mg of paracetamol." and row.error is None
    assert json.loads((summary.run_dir / str(row.raw_response_path)).read_text())["results"]
    assert len(bodies[0]) == 44 + 16000  # WAV header + 0.5 s of 16 kHz PCM16
