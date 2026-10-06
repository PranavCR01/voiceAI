"""What a batch STT adapter must provide, and the errors the runner understands.

Adapters raise `RetryableError` for transient failures (rate limits, 5xx, timeouts) and
`PermanentError` for anything that will fail again (bad auth, unsupported audio). Any other
exception is treated as permanent. The streaming adapter protocol lives with the streaming
trace format (#14, #18).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import JsonValue


class AdapterError(Exception):
    """Base for errors an adapter raises deliberately."""


class RetryableError(AdapterError):
    """Transient: worth retrying with backoff (HTTP 429, 5xx, timeouts, dropped connections)."""


class PermanentError(AdapterError):
    """Will fail again: bad request, auth failure, unsupported audio."""


@dataclass(frozen=True)
class Transcript:
    text: str  # as the provider formatted it; normalization happens at scoring time
    raw: JsonValue | bytes  # the provider's response, stored next to the result
    raw_suffix: str = ".json"


class BatchAdapter(Protocol):
    async def transcribe(self, clip: Any, settings: Mapping[str, JsonValue]) -> Transcript:
        """Transcribe one clip. `clip` is whatever the run's clip loader returns (#12)."""
        ...
