"""Deepgram streaming: Nova-3 (`/v1/listen`) and Flux (`/v2/listen`), chosen by model id.

Protocol checked against developers.deepgram.com on 2026-11-05 (docs/RESEARCH.md). Mapping to
trace events (harness/streaming/README.md):

Nova-3
- `Results` with `is_final: false` and text -> `partial`; `is_final: true` -> `final` (words in
  seconds from stream start -> ms; the stream starts at the clip's first sample, so that is audio
  time); `speech_final: true` -> also `endpoint`.
- `UtteranceEnd` -> `endpoint` (except `last_word_end: -1`, which the docs say to ignore);
  `SpeechStarted` -> `vad_event`; `Error` -> `error`; `Metadata` (sent after CloseStream) ends
  the session.
- Forced finalize: `{"type": "Finalize"}`; close: `{"type": "CloseStream"}`.

Flux
- `TurnInfo` `Update` / `StartOfTurn` / `EagerEndOfTurn` / `TurnResumed` -> `partial`
  (`StartOfTurn` also `vad_event`); `EndOfTurn` -> `final`, plus `endpoint` unless its trigger is
  `manual` (our own ForceEndTurn is not the provider's endpointing).
- Forced finalize: `{"type": "ForceEndTurn"}`. Close: ForceEndTurn then CloseStream, because
  CloseStream alone sends no EndOfTurn and the last turn's words would be lost.
- Word `start`/`end` are optional in Flux; finals without them carry no word timings.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode, urlsplit

from pydantic import JsonValue

from harness.audio import Encoding
from harness.providers.http import check_settings, resolve_keyterms
from harness.providers.registry import ProviderConfig
from harness.streaming.session import Mapped, Message
from harness.streaming.trace import EventKind

PROVIDER = "deepgram"
HOST = "api.deepgram.com"
NOVA_SETTINGS = frozenset(
    {
        "interim_results",
        "smart_format",
        "punctuate",
        "numerals",
        "endpointing",
        "utterance_end_ms",
        "vad_events",
        "language",
        "keyterms",
    }
)
FLUX_SETTINGS = frozenset({"eot_threshold", "eager_eot_threshold", "eot_timeout_ms", "keyterms"})


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


def _words(items: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Provider words (seconds) -> trace words (ms); None when any word lacks timings."""
    if not items:
        return None
    out = []
    for w in items:
        if w.get("start") is None or w.get("end") is None:
            return None
        text = w.get("punctuated_word") or w.get("word") or ""
        out.append(
            {"text": text, "start_ms": float(w["start"]) * 1000, "end_ms": float(w["end"]) * 1000}
        )
    return out


class DeepgramStream:
    def __init__(
        self,
        config: ProviderConfig,
        api_key: str,
        settings: Mapping[str, JsonValue],
        keyterms: list[str] | None,
        encoding: Encoding,
    ) -> None:
        self.flux = config.model_id.startswith("flux")
        check_settings(PROVIDER, settings, FLUX_SETTINGS if self.flux else NOVA_SETTINGS)
        self.model_id = config.model_id
        self.api_key = api_key
        self.encoding: Encoding = encoding
        self.settings = {k: v for k, v in settings.items() if k != "keyterms"}
        self.keyterms = resolve_keyterms(PROVIDER, settings, keyterms)
        self.host = urlsplit(config.base_url).netloc if config.base_url else HOST
        self.finalize_supported = True

    def reset(self) -> None:
        pass

    def url(self) -> str:
        audio = (
            [("encoding", "mulaw"), ("sample_rate", "8000")]
            if self.encoding == "mulaw"
            else [("encoding", "linear16"), ("sample_rate", "16000")]
        )
        params = [("model", self.model_id), *audio]
        params += [(k, _q(v)) for k, v in sorted(self.settings.items())]
        params += [("keyterm", t) for t in self.keyterms]
        path = "/v2/listen" if self.flux else "/v1/listen"
        return f"wss://{self.host}{path}?{urlencode(params)}"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Token {self.api_key}"}

    def audio_frame(self, data: bytes) -> Message:
        return data

    def finalize_frame(self) -> str | None:
        return json.dumps({"type": "ForceEndTurn" if self.flux else "Finalize"})

    def close_frames(self) -> list[str]:
        if self.flux:
            return [json.dumps({"type": "ForceEndTurn"}), json.dumps({"type": "CloseStream"})]
        return [json.dumps({"type": "CloseStream"})]

    def handle(self, message: Message) -> list[Mapped]:
        m = _json(message)
        return self._flux(m) if self.flux else self._nova(m)

    def is_terminal(self, message: Message) -> bool:
        # Nova-3 sends Metadata last after CloseStream; Flux just closes the socket.
        return not self.flux and _json(message).get("type") == "Metadata"

    @staticmethod
    def _nova(m: dict[str, Any]) -> list[Mapped]:
        kind = m.get("type")
        if kind == "Results":
            alt = (m.get("channel") or {}).get("alternatives") or [{}]
            text = alt[0].get("transcript") or ""
            out: list[Mapped] = []
            if m.get("is_final"):
                out.append(
                    Mapped(EventKind.FINAL, {"text": text, "words": _words(alt[0].get("words"))})
                )
            elif text:
                out.append(Mapped(EventKind.PARTIAL, {"text": text}))
            if m.get("speech_final"):
                out.append(Mapped(EventKind.ENDPOINT))
            return out
        if kind == "UtteranceEnd":
            return [] if m.get("last_word_end") == -1 else [Mapped(EventKind.ENDPOINT)]
        if kind == "SpeechStarted":
            return [Mapped(EventKind.VAD_EVENT)]
        if kind == "Error":
            return [Mapped(EventKind.ERROR)]
        return []

    @staticmethod
    def _flux(m: dict[str, Any]) -> list[Mapped]:
        kind = m.get("type")
        if kind == "TurnInfo":
            event = m.get("event")
            text = m.get("transcript") or ""
            if event == "EndOfTurn":
                out = [Mapped(EventKind.FINAL, {"text": text, "words": _words(m.get("words"))})]
                if m.get("trigger") != "manual":
                    out.append(Mapped(EventKind.ENDPOINT))
                return out
            out = [Mapped(EventKind.VAD_EVENT)] if event == "StartOfTurn" else []
            if text:
                out.append(Mapped(EventKind.PARTIAL, {"text": text}))
            return out
        if kind == "Error":
            return [Mapped(EventKind.ERROR)]
        return []
