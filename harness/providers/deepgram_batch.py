"""Deepgram pre-recorded transcription (POST /v1/listen with the audio as the body).

Written from memory of Deepgram's API because its docs are unreachable from the cloud
environment; every item marked VERIFY in harness/providers/README.md must be checked
against current docs before the first live run.
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

PROVIDER = "deepgram"
URL = "https://api.deepgram.com/v1/listen"
# setting name -> query parameter (booleans are sent as "true"/"false")
_PARAMS = {"smart_format": "smart_format", "punctuate": "punctuate", "language": "language"}
SETTINGS = frozenset({*_PARAMS, "keyterms"})
Params = list[tuple[str, str | int | float | bool | None]]


class DeepgramBatch:
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

    def params(self, settings: Mapping[str, JsonValue]) -> Params:
        params: Params = [("model", self.model_id)]
        for name, param in _PARAMS.items():
            if name in settings:
                value = settings[name]
                params.append(
                    (param, str(value).lower() if isinstance(value, bool) else str(value))
                )
        params += [("keyterm", term) for term in self.keyterms]  # repeated parameter
        return params

    async def transcribe(self, clip: AudioClip, settings: Mapping[str, JsonValue]) -> Transcript:
        request = self.client.build_request(
            "POST",
            URL,
            params=self.params(settings),
            headers={"Authorization": f"Token {self.api_key}", "Content-Type": "audio/wav"},
            content=to_wav_bytes(clip),
        )
        response = await send(self.client, PROVIDER, request)
        raise_for_status(response, PROVIDER)
        body = parse_json(response, PROVIDER)
        return Transcript(text=extract_text(body), raw=body)


def extract_text(body: object) -> str:
    try:
        channels = body["results"]["channels"]  # type: ignore[index]
        return str(channels[0]["alternatives"][0]["transcript"])
    except (KeyError, IndexError, TypeError) as e:
        raise PermanentError(f"{PROVIDER}: unexpected response shape: {e!r}") from e
