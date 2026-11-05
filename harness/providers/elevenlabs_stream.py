"""ElevenLabs Scribe v2 Realtime (`wss://api.elevenlabs.io/v1/speech-to-text/realtime`).

Protocol checked against elevenlabs.io/docs on 2026-11-05 (docs/RESEARCH.md). Mapping:
- `partial_transcript` with text -> `partial` (empty ones are keep-alives).
- `committed_transcript` -> `endpoint` when the provider committed on its own (VAD silence or
  turn prediction). A commit answering one we sent (forced finalize, or the commit after the last
  audio) is not the provider's endpointing and is recorded as `info`: replies are matched to our
  commits in order. Probe 2026-11-05: with the default 1.5 s VAD silence and 1.5 s of trailing
  silence, our closing commit always arrived first and was being counted as the endpoint.
- `committed_transcript_with_timestamps` -> `final` with words (`type: word` only; seconds ->
  ms; the docs don't state the reference point, assumed stream start = audio time, to be
  confirmed on a live session).
- Error message types -> `error`, and they end the session.
- Audio goes as JSON with base64 (`input_audio_chunk`). Forced finalize = a manual commit
  (empty chunk with `commit: true`).
- There is no close message and no terminal message. After the last audio the session sends a
  commit; the committed transcript answering it ends the session (else the drain timeout).
- Default `commit_strategy` here is `vad` so `natural` mode measures the provider's endpointing.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from pydantic import JsonValue

from harness.audio import Encoding
from harness.providers.http import check_settings, no_base_url, resolve_keyterms
from harness.providers.registry import ProviderConfig
from harness.streaming.session import Mapped, Message
from harness.streaming.trace import EventKind

PROVIDER = "elevenlabs"
URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime"
SETTINGS = frozenset(
    {
        "commit_strategy",
        "vad_silence_threshold_secs",
        "vad_threshold",
        "min_speech_duration_ms",
        "min_silence_duration_ms",
        "language_code",
        "no_verbatim",
        "keyterms",
    }
)
ERRORS = frozenset(
    {
        "error",
        "auth_error",
        "quota_exceeded",
        "commit_throttled",
        "unaccepted_terms",
        "rate_limited",
        "queue_overflow",
        "resource_exhausted",
        "session_time_limit_exceeded",
        "input_error",
        "invalid_request",
        "chunk_size_exceeded",
        "insufficient_audio_activity",
        "transcriber_error",
    }
)
MAX_KEYTERMS, MAX_KEYTERM_CHARS = 50, 20  # documented realtime limits


def _q(value: JsonValue) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def _json(message: Message) -> dict[str, Any]:
    if isinstance(message, bytes):
        return {}
    try:
        parsed = json.loads(message)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class ElevenLabsStream:
    def __init__(
        self,
        config: ProviderConfig,
        api_key: str,
        settings: Mapping[str, JsonValue],
        keyterms: list[str] | None,
        encoding: Encoding,
    ) -> None:
        check_settings(PROVIDER, settings, SETTINGS)
        no_base_url(PROVIDER, config.base_url)
        self.model_id = config.model_id
        self.api_key = api_key
        self.encoding: Encoding = encoding
        self.rate = 8000 if encoding == "mulaw" else 16000
        self.settings: dict[str, JsonValue] = {"commit_strategy": "vad"}
        self.settings.update({k: v for k, v in settings.items() if k != "keyterms"})
        self.keyterms = resolve_keyterms(PROVIDER, settings, keyterms)
        if len(self.keyterms) > MAX_KEYTERMS or any(
            len(t) > MAX_KEYTERM_CHARS for t in self.keyterms
        ):
            raise ValueError(
                f"{PROVIDER}: realtime allows <= {MAX_KEYTERMS} keyterms of <= {MAX_KEYTERM_CHARS}"
                " chars"
            )
        self.finalize_supported = True
        self._closing = False
        self._own_commits = 0  # commits we sent whose committed_transcript hasn't arrived yet

    def reset(self) -> None:
        self._closing = False
        self._own_commits = 0

    def url(self) -> str:
        fmt = "ulaw_8000" if self.encoding == "mulaw" else "pcm_16000"
        params = [
            ("model_id", self.model_id),
            ("audio_format", fmt),
            ("include_timestamps", "true"),
        ]
        params += [(k, _q(v)) for k, v in sorted(self.settings.items())]
        params += [("keyterms", t) for t in self.keyterms]
        return f"{URL}?{urlencode(params)}"

    def headers(self) -> dict[str, str]:
        return {"xi-api-key": self.api_key}

    def _chunk(self, data: bytes, commit: bool) -> str:
        return json.dumps(
            {
                "message_type": "input_audio_chunk",
                "audio_base_64": base64.b64encode(data).decode("ascii"),
                "commit": commit,
                "sample_rate": self.rate,
            }
        )

    def audio_frame(self, data: bytes) -> Message:
        return self._chunk(data, False)

    def finalize_frame(self) -> str | None:
        self._own_commits += 1
        return self._chunk(b"", True)

    def close_frames(self) -> list[str]:
        self._closing = True
        self._own_commits += 1
        return [self._chunk(b"", True)]

    def handle(self, message: Message) -> list[Mapped]:
        m = _json(message)
        kind = m.get("message_type")
        text = m.get("text") or ""
        if kind == "partial_transcript":
            return [Mapped(EventKind.PARTIAL, {"text": text})] if text else []
        if kind == "committed_transcript":
            if self._own_commits > 0:
                self._own_commits -= 1
                return [Mapped(EventKind.INFO)]
            return [Mapped(EventKind.ENDPOINT)]
        if kind == "committed_transcript_with_timestamps":
            words = [
                {
                    "text": w["text"],
                    "start_ms": float(w["start"]) * 1000,
                    "end_ms": float(w["end"]) * 1000,
                }
                for w in m.get("words") or []
                if w.get("type", "word") == "word" and w.get("start") is not None
            ]
            return [Mapped(EventKind.FINAL, {"text": text, "words": words or None})]
        if kind in ERRORS:
            return [Mapped(EventKind.ERROR)]
        return []

    def is_terminal(self, message: Message) -> bool:
        kind = _json(message).get("message_type")
        return kind in ERRORS or (self._closing and kind == "committed_transcript_with_timestamps")
