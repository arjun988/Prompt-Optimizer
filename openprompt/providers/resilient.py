"""Resilient provider wrapper with retries."""

from __future__ import annotations

from typing import Any, Iterator

from openprompt.providers.base import Message, ModelResponse
from openprompt.providers.retry import map_http_error, with_retry


class ResilientProvider:
    """Wrap a provider with retry logic and normalized errors."""

    def __init__(self, inner: Any, *, max_attempts: int = 3) -> None:
        self._inner = inner
        self.name = getattr(inner, "name", "unknown")
        self.model = getattr(inner, "model", "unknown")
        self._max_attempts = max_attempts

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        def _call() -> ModelResponse:
            try:
                return self._inner.generate(messages, **kwargs)
            except Exception as exc:
                raise map_http_error(self.name, exc) from exc

        return with_retry(_call, max_attempts=self._max_attempts)

    def stream(self, messages: list[Message], **kwargs: Any) -> Iterator[str]:
        if not hasattr(self._inner, "stream"):
            response = self.generate(messages, **kwargs)
            yield response.content
            return
        yield from self._inner.stream(messages, **kwargs)
