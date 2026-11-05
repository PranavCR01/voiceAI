"""AssemblyAI streaming (v3, `wss://streaming.assemblyai.com/v3/ws`).

Protocol checked against assemblyai.com/docs on 2026-11-05 (docs/RESEARCH.md). Mapping:
- `Turn` with `end_of_turn: false` and text -> `partial` (each Turn supersedes the previous one
  for the same `turn_order`).
- The first `end_of_turn: true` per turn -> `endpoint`. The turn's `final` is the end-of-turn
  message that is formatted (`turn_is_formatted`), or, when no formatted message is expected
  (Universal Streaming models without `format_turns`), the first end-of-turn message. Words are
  integer ms from the start of the stream = audio time.
- `SpeechStarted` -> `vad_event`; `Error` -> `error`; `Termination` (always last) ends the session.
- Forced finalize: `{"type": "ForceEndpoint"}`; close: `{"type": "Terminate"}`.
- Billing is on session (WebSocket-open) duration, not audio: the registry's billing_basis says so.
"""

from __future__ import annotations

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

PROVIDER = "assemblyai"
URL = "wss://streaming.assemblyai.com/v3/ws"
SETTINGS = frozenset(
    {
        "mode",
        "min_turn_silence",
        "max_turn_silence",
        "vad_threshold",
        "end_of_turn_confidence_threshold",
        "interruption_delay",
        "format_turns",
        "include_partial_turns",
        "language_codes",
        "domain",
        "keyterms",
    }
)
MAX_KEYTERMS = 100  # documented streaming limit; each term <= 50 chars


def _q(value: JsonValue) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, list | dict):
        return json.dumps(value)
    return str(value)


def _json(message: Message) -> dict[str, Any]:
    if isinstance(message, bytes):
        return {}
    try:
        parsed = json.loads(message)
    except ValueError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


class AssemblyAIStream:
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
        self.settings = {k: v for k, v in settings.items() if k != "keyterms"}
        self.keyterms = resolve_keyterms(PROVIDER, settings, keyterms)
        if len(self.keyterms) > MAX_KEYTERMS or any(len(t) > 50 for t in self.keyterms):
            raise ValueError(
                f"{PROVIDER}: streaming allows <= {MAX_KEYTERMS} keyterms of <= 50 chars"
            )
        # Universal Streaming models send one unformatted end-of-turn message unless format_turns
        # is on; the Universal-3 Pro models always format.
        legacy = self.model_id.startswith("universal-streaming")
        self.expect_formatted = bool(settings.get("format_turns")) or not legacy
        self.finalize_supported = True
        self._ended: set[int] = set()
        self._finalized: set[int] = set()

    def reset(self) -> None:
        self._ended.clear()
        self._finalized.clear()

    def url(self) -> str:
        audio = (
            [("encoding", "pcm_mulaw"), ("sample_rate", "8000")]
            if self.encoding == "mulaw"
            else [("encoding", "pcm_s16le"), ("sample_rate", "16000")]
        )
        params = [("speech_model", self.model_id), *audio]
        params += [(k, _q(v)) for k, v in sorted(self.settings.items())]
        if self.keyterms:
            params.append(("keyterms_prompt", json.dumps(self.keyterms)))
        return f"{URL}?{urlencode(params)}"

    def headers(self) -> dict[str, str]:
        return {"Authorization": self.api_key}

    def audio_frame(self, data: bytes) -> Message:
        return data

    def finalize_frame(self) -> str | None:
        return json.dumps({"type": "ForceEndpoint"})

    def close_frames(self) -> list[str]:
        return [json.dumps({"type": "Terminate"})]

    def handle(self, message: Message) -> list[Mapped]:
        m = _json(message)
        kind = m.get("type")
        if kind == "Turn":
            order = int(m.get("turn_order", -1))
            text = m.get("transcript") or ""
            if not m.get("end_of_turn"):
                return [Mapped(EventKind.PARTIAL, {"text": text})] if text else []
            out: list[Mapped] = []
            if order not in self._ended:
                self._ended.add(order)
                out.append(Mapped(EventKind.ENDPOINT))
            formatted = bool(m.get("turn_is_formatted"))
            if order not in self._finalized and (formatted or not self.expect_formatted):
                self._finalized.add(order)
                words = [
                    {"text": w["text"], "start_ms": float(w["start"]), "end_ms": float(w["end"])}
                    for w in m.get("words") or []
                    if w.get("start") is not None and w.get("end") is not None
                ]
                out.insert(0, Mapped(EventKind.FINAL, {"text": text, "words": words or None}))
            elif text and order not in self._finalized:
                out.append(Mapped(EventKind.PARTIAL, {"text": text}))
            return out
        if kind == "SpeechStarted":
            return [Mapped(EventKind.VAD_EVENT)]
        if kind == "Error":
            return [Mapped(EventKind.ERROR)]
        return []

    def is_terminal(self, message: Message) -> bool:
        return _json(message).get("type") in ("Termination", "Error")
