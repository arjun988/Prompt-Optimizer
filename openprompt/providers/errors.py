"""Provider error types."""

from __future__ import annotations


class ProviderError(Exception):
    """Base error for model provider failures."""

    def __init__(self, message: str, *, provider: str = "", status_code: int | None = None) -> None:
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class ProviderAuthError(ProviderError):
    """Invalid or missing API credentials."""


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded (HTTP 429)."""


class ProviderTimeoutError(ProviderError):
    """Request timed out."""


class ProviderUnavailableError(ProviderError):
    """Temporary upstream failure."""
