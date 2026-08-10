"""Retry helpers for provider calls."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from openprompt.providers.errors import (
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

T = TypeVar("T")

RETRYABLE = (ProviderRateLimitError, ProviderTimeoutError, ProviderUnavailableError)


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 8.0,
) -> T:
    """Execute *fn* with exponential backoff on retryable provider errors."""
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except RETRYABLE as exc:
            last_exc = exc
            if attempt == max_attempts - 1:
                raise
            delay = min(max_delay, base_delay * (2**attempt))
            time.sleep(delay)
        except ProviderError:
            raise
    raise last_exc  # pragma: no cover


def map_http_error(provider: str, exc: Exception) -> ProviderError:
    """Map common HTTP/SDK exceptions to ProviderError."""
    message = str(exc)
    lower = message.lower()
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)

    if status == 401 or status == 403 or "api key" in lower or "unauthorized" in lower:
        from openprompt.providers.errors import ProviderAuthError

        return ProviderAuthError(message, provider=provider, status_code=status)
    if status == 429 or "rate limit" in lower or "too many requests" in lower:
        return ProviderRateLimitError(message, provider=provider, status_code=429)
    if "timeout" in lower or "timed out" in lower:
        return ProviderTimeoutError(message, provider=provider)
    if status in {500, 502, 503, 504}:
        return ProviderUnavailableError(message, provider=provider, status_code=status)
    return ProviderError(message, provider=provider, status_code=status)
