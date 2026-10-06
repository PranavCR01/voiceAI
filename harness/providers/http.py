"""Shared HTTP plumbing for batch adapters: one client per adapter, and one place that decides
which failures are worth retrying."""

from __future__ import annotations

import json
from collections.abc import Collection, Mapping
from typing import Any

import httpx
from pydantic import JsonValue

from harness.providers.base import PermanentError, RetryableError

DEFAULT_TIMEOUT_S = 120.0
_RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504})


def check_settings(
    provider: str, settings: Mapping[str, JsonValue], known: Collection[str]
) -> None:
    """Reject settings an adapter doesn't map, so a typo can't silently become a default."""
    unknown = sorted(set(settings) - set(known))
    if unknown:
        raise ValueError(f"{provider}: unsupported settings {unknown}; supported: {sorted(known)}")


def resolve_keyterms(
    provider: str, settings: Mapping[str, JsonValue], keyterms: list[str] | None
) -> list[str]:
    """`keyterms: "profile"` means the profile's keyterm list; a list is used as given."""
    value = settings.get("keyterms")
    if value is None:
        return []
    if value == "profile":
        if not keyterms:
            raise ValueError(f"{provider}: keyterms 'profile' needs --profile with keyterms")
        return list(keyterms)
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return [str(v) for v in value]
    raise ValueError(f"{provider}: keyterms must be 'profile' or a list of strings")


def raise_for_status(response: httpx.Response, provider: str) -> None:
    if response.is_success:
        return
    detail = response.text[:300]
    message = f"{provider} HTTP {response.status_code}: {detail}"
    if response.status_code in _RETRYABLE_STATUS:
        raise RetryableError(message)
    raise PermanentError(message)


def parse_json(response: httpx.Response, provider: str) -> Any:
    try:
        return response.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise PermanentError(f"{provider}: malformed JSON response: {e}") from e


async def send(client: httpx.AsyncClient, provider: str, request: httpx.Request) -> httpx.Response:
    """Send, mapping transport failures (timeouts, dropped connections) to RetryableError."""
    try:
        return await client.send(request)
    except (httpx.TimeoutException, httpx.TransportError) as e:
        raise RetryableError(f"{provider}: {type(e).__name__}: {e}") from e
