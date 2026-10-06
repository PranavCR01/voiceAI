"""AssemblyAI async transcription: upload the audio, create a transcript, poll until done.

Written from memory of AssemblyAI's v2 API because its docs are unreachable from the cloud
environment; every item marked VERIFY in harness/providers/README.md must be checked against
current docs before the first live run.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx
from pydantic import JsonValue

from harness.audio import AudioClip, to_wav_bytes
from harness.providers.base import PermanentError, RetryableError, Transcript
from harness.providers.http import (
    DEFAULT_TIMEOUT_S,
    check_settings,
    parse_json,
    raise_for_status,
    resolve_keyterms,
    send,
)
from harness.providers.registry import ProviderConfig

PROVIDER = "assemblyai"
BASE = "https://api.assemblyai.com/v2"
# setting name -> transcript request field
_FIELDS = {"format_text": "format_text", "punctuate": "punctuate", "language_code": "language_code"}
SETTINGS = frozenset({*_FIELDS, "keyterms"})
POLL_INTERVAL_S = 1.0
POLL_TIMEOUT_S = 600.0


class AssemblyAIBatch:
    def __init__(
        self,
        config: ProviderConfig,
        api_key: str,
        *,
        keyterms: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        poll_interval_s: float = POLL_INTERVAL_S,
        poll_timeout_s: float = POLL_TIMEOUT_S,
    ) -> None:
        check_settings(PROVIDER, config.settings, SETTINGS)
        self.model_id = config.model_id
        self.keyterms = resolve_keyterms(PROVIDER, config.settings, keyterms)
        self.headers = {"authorization": api_key}
        self.client = client or httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_S)
        self.sleep = sleep
        self.poll_interval_s = poll_interval_s
        self.poll_timeout_s = poll_timeout_s

    def body(self, upload_url: str, settings: Mapping[str, JsonValue]) -> dict[str, Any]:
        body: dict[str, Any] = {"audio_url": upload_url, "speech_model": self.model_id}
        for name, field in _FIELDS.items():
            if name in settings:
                body[field] = settings[name]
        if self.keyterms:
            body["keyterms_prompt"] = self.keyterms
        return body

    async def _json(self, request: httpx.Request) -> Any:
        response = await send(self.client, PROVIDER, request)
        raise_for_status(response, PROVIDER)
        return parse_json(response, PROVIDER)

    async def transcribe(self, clip: AudioClip, settings: Mapping[str, JsonValue]) -> Transcript:
        upload = await self._json(
            self.client.build_request(
                "POST", f"{BASE}/upload", headers=self.headers, content=to_wav_bytes(clip)
            )
        )
        upload_url = _field(upload, "upload_url")
        created = await self._json(
            self.client.build_request(
                "POST",
                f"{BASE}/transcript",
                headers=self.headers,
                json=self.body(upload_url, settings),
            )
        )
        transcript_id = _field(created, "id")
        waited = 0.0
        while True:
            body = await self._json(
                self.client.build_request(
                    "GET", f"{BASE}/transcript/{transcript_id}", headers=self.headers
                )
            )
            status = body.get("status") if isinstance(body, dict) else None
            if status == "completed":
                return Transcript(text=str(body.get("text") or ""), raw=body)
            if status == "error":
                raise PermanentError(
                    f"{PROVIDER}: transcript {transcript_id} failed: {body.get('error')}"
                )
            if status not in ("queued", "processing"):
                raise PermanentError(f"{PROVIDER}: unexpected status {status!r}")
            if waited >= self.poll_timeout_s:
                raise RetryableError(
                    f"{PROVIDER}: transcript {transcript_id} not done after {waited:.0f}s"
                )
            await self.sleep(self.poll_interval_s)
            waited += self.poll_interval_s


def _field(body: Any, name: str) -> str:
    if not isinstance(body, dict) or not body.get(name):
        raise PermanentError(f"{PROVIDER}: response missing {name!r}")
    return str(body[name])
