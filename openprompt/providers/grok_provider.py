"""xAI Grok provider (OpenAI-compatible API)."""

from __future__ import annotations

import os
import time
from typing import Any

from openprompt.config.model_catalog import default_model_for
from openprompt.providers.base import Message, ModelResponse

DEFAULT_BASE_URL = "https://api.x.ai/v1"


class GrokProvider:
    """
    xAI Grok chat completions.

    Uses the OpenAI Python SDK against xAI's compatible endpoint.
    Set ``XAI_API_KEY`` or pass ``api_key`` explicitly.
    """

    name = "grok"

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model or default_model_for("grok")
        self.api_key = api_key or os.environ.get("XAI_API_KEY")
        self.base_url = (base_url or os.environ.get("XAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        if not self.api_key:
            raise ValueError("Grok API key required. Set XAI_API_KEY or pass api_key.")

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "Grok uses the OpenAI SDK. Install with: pip install 'openprompt[grok]'"
            ) from exc

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
            raw={"id": response.id, "provider": "grok"},
        )
