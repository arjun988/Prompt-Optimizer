"""OpenRouter provider (OpenAI-compatible API)."""

from __future__ import annotations

import os
import time
from typing import Any, Iterator

from openprompt.config.model_catalog import default_model_for
from openprompt.providers.base import Message, ModelResponse

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or default_model_for("openrouter")
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        self.base_url = (base_url or os.environ.get("OPENROUTER_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        if not self.api_key:
            raise ValueError("OpenRouter API key required. Set OPENROUTER_API_KEY.")

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install openai: pip install 'openprompt[openai]'") from exc

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        start = time.perf_counter()
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
        )
        latency_ms = (time.perf_counter() - start) * 1000
        choice = response.choices[0]
        usage = response.usage
        return ModelResponse(
            content=choice.message.content or "",
            model=response.model,
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            latency_ms=latency_ms,
            raw={"id": response.id, "provider": "openrouter"},
        )

    def stream(self, messages: list[Message], **kwargs: Any) -> Iterator[str]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError("Install openai: pip install 'openprompt[openai]'") from exc

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        stream = client.chat.completions.create(
            model=self.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=kwargs.get("temperature", 0.7),
            max_tokens=kwargs.get("max_tokens", 4096),
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
