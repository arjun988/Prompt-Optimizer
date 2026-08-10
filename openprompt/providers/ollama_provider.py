"""Ollama local model provider."""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

from openprompt.providers.base import Message, ModelResponse


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "llama3.2", base_url: str | None = None) -> None:
        self.model = model
        self.base_url = (base_url or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
            },
        }

        start = time.perf_counter()
        with httpx.Client(timeout=120.0) as client:
            response = client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        latency_ms = (time.perf_counter() - start) * 1000
        content = data.get("message", {}).get("content", "")
        prompt_eval = data.get("prompt_eval_count", 0)
        eval_count = data.get("eval_count", 0)

        return ModelResponse(
            content=content,
            model=self.model,
            input_tokens=prompt_eval or max(1, len(str(payload)) // 4),
            output_tokens=eval_count or max(1, len(content) // 4),
            latency_ms=latency_ms,
            raw=data,
        )
