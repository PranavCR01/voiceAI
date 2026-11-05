"""ElevenLabs Scribe batch transcription (POST /v1/speech-to-text, multipart upload).

Checked against the API reference on 2026-11-05 (docs/RESEARCH.md); not yet run live, because
api.elevenlabs.io is blocked from the cloud environment. Open items: harness/providers/README.md.

Audio-event tagging is forced off: Scribe can insert tags such as "(laughter)" that are not
speech. The normalizer would drop parenthesized text anyway, but the raw output should be clean.

Keyterms are checked against the documented limits before any request, and more than 100 are
refused: above 100 the API bills every request for at least 20 s of audio, which on short
utterances (PriMock57's are a few seconds) multiplies the cost several times over.
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
    no_base_url,
    parse_json,
    raise_for_status,
    resolve_keyterms,
    send,
)
from harness.providers.registry import ProviderConfig

PROVIDER = "elevenlabs"
URL = "https://api.elevenlabs.io/v1/speech-to-text"
_FIELDS = {
    name: name for name in ("language_code", "diarize", "no_verbatim", "temperature", "seed")
}
SETTINGS = frozenset({*_FIELDS, "keyterms"})

# Documented keyterm limits (batch): at most 1000 terms, 50 characters and 5 words each, none of
# these characters. MAX_KEYTERMS is ours: the 20 s minimum billable duration starts above 100.
MAX_KEYTERMS = 100
_KEYTERM_MAX_CHARS = 50
_KEYTERM_MAX_WORDS = 5
_KEYTERM_BAD_CHARS = frozenset("<>{}[]\\")


def check_keyterms(terms: list[str]) -> None:
    if len(terms) > MAX_KEYTERMS:
        raise ValueError(
            f"{PROVIDER}: {len(terms)} keyterms; above {MAX_KEYTERMS} every request is billed for"
            " at least 20 s of audio, so this adapter refuses them"
        )
    for term in terms:
        if (
            not term.strip()
            or len(term) > _KEYTERM_MAX_CHARS
            or len(term.split()) > _KEYTERM_MAX_WORDS
            or _KEYTERM_BAD_CHARS.intersection(term)
        ):
            raise ValueError(
                f"{PROVIDER}: keyterm {term!r} breaks the documented limits (non-empty,"
                f" <= {_KEYTERM_MAX_CHARS} chars, <= {_KEYTERM_MAX_WORDS} words,"
                " none of <>{}[]\\)"
            )


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
        no_base_url(PROVIDER, config.base_url)
        self.model_id = config.model_id
        self.keyterms = resolve_keyterms(PROVIDER, config.settings, keyterms)
        check_keyterms(self.keyterms)
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
