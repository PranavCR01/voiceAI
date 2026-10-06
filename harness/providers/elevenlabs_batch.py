"""ElevenLabs Scribe batch transcription (POST /v1/speech-to-text, multipart upload).

Written from memory of ElevenLabs' API because its docs are unreachable from the cloud
environment; every item marked VERIFY in harness/providers/README.md must be checked against
current docs before the first live run.

Audio-event tagging is forced off: Scribe can insert tags such as "(laughter)" that are not
speech. The normalizer would drop parenthesized text anyway, but the raw output should be clean.
"""

from __future__ import annotations

from collections.abc import Mapping

import httpx
from pydantic import JsonValue

from harness.audio import AudioClip, to_wav_bytes
from harness.providers.base import PermanentError, Transcript
from harness.providers.http import (
    DEFAULT_TIMEOUT_S,
    check_settings,
    parse_json,
    raise_for_status,
    resolve_keyterms,
    send,
)
from harness.providers.registry import ProviderConfig

PROVIDER = "elevenlabs"
URL = "https://api.elevenlabs.io/v1/speech-to-text"
_FIELDS = {"language_code": "language_code", "diarize": "diarize"}
SETTINGS = frozenset({*_FIELDS, "keyterms"})


def _form_value(value: JsonValue) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


class ElevenLabsBatch:
    def __init__(
        self,
        config: ProviderConfig,
        api_key: str,
        *,
        keyterms: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        check_settings(PROVIDER, config.settings, SETTINGS)
        self.model_id = config.model_id
        self.keyterms = resolve_keyterms(PROVIDER, config.settings, keyterms)
        self.api_key = api_key
        self.client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S)

    def form(self, settings: Mapping[str, JsonValue]) -> list[tuple[str, str]]:
        form = [("model_id", self.model_id), ("tag_audio_events", "false")]
        form += [
            (field, _form_value(settings[name]))
            for name, field in _FIELDS.items()
            if name in settings
        ]
        form += [("keyterms", term) for term in self.keyterms]
        return form

    def multipart(
        self, clip: AudioClip, settings: Mapping[str, JsonValue]
    ) -> list[tuple[str, tuple[str | None, bytes | str, str | None]]]:
        """Form fields (no filename, so sent as plain fields; repeats allowed) plus the audio."""
        parts: list[tuple[str, tuple[str | None, bytes | str, str | None]]] = [
            (name, (None, value, None)) for name, value in self.form(settings)
        ]
        parts.append(("file", ("audio.wav", to_wav_bytes(clip), "audio/wav")))
        return parts

    async def transcribe(self, clip: AudioClip, settings: Mapping[str, JsonValue]) -> Transcript:
        request = self.client.build_request(
            "POST", URL, headers={"xi-api-key": self.api_key}, files=self.multipart(clip, settings)
        )
        response = await send(self.client, PROVIDER, request)
        raise_for_status(response, PROVIDER)
        body = parse_json(response, PROVIDER)
        if not isinstance(body, dict) or "text" not in body:
            raise PermanentError(f"{PROVIDER}: unexpected response shape (no 'text')")
        return Transcript(text=str(body["text"]), raw=body)
