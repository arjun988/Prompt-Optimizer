"""Anthropic Messages API provider."""

from __future__ import annotations

import os
import time
from typing import Any

from openprompt.config.model_catalog import default_model_for
from openprompt.providers.base import Message, ModelResponse


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or default_model_for("anthropic")
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key required. Set ANTHROPIC_API_KEY or pass api_key.")

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        try:
            import anthropic
        except ImportError as exc:
            raise ImportError("Install anthropic: pip install 'openprompt[anthropic]'") from exc

        client = anthropic.Anthropic(api_key=self.api_key)

        system_parts: list[str] = []
        api_messages: list[dict[str, str]] = []
        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
            else:
                api_messages.append({"role": message.role, "content": message.content})

        start = time.perf_counter()
        response = client.messages.create(
            model=self.model,
            max_tokens=kwargs.get("max_tokens", 4096),
            system="\n\n".join(system_parts) if system_parts else anthropic.NOT_GIVEN,
            messages=api_messages,
            temperature=kwargs.get("temperature", 0.7),
        )
        latency_ms = (time.perf_counter() - start) * 1000

        text_blocks = [block.text for block in response.content if block.type == "text"]
        return ModelResponse(
            content="\n".join(text_blocks),
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            latency_ms=latency_ms,
            raw={"id": response.id},
        )
