"""Mock provider for offline development and tests."""

from __future__ import annotations

import hashlib
import time
from typing import Any

from openprompt.providers.base import Message, ModelResponse


class MockProvider:
    """Deterministic responses without calling external APIs."""

    name = "mock"

    def __init__(self, model: str = "mock-model") -> None:
        self.model = model

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        start = time.perf_counter()
        prompt_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
        digest = hashlib.sha256(prompt_text.encode()).hexdigest()[:12]

        content = self._mock_response(messages, digest)
        input_tokens = max(1, len(prompt_text) // 4)
        output_tokens = max(1, len(content) // 4)
        latency_ms = (time.perf_counter() - start) * 1000

        return ModelResponse(
            content=content,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def _mock_response(self, messages: list[Message], digest: str) -> str:
        last = messages[-1].content.lower() if messages else ""

        if "optimize" in last or "improve" in last:
            return (
                "You are an expert assistant.\n\n"
                "Task: Complete the requested analysis with clear, measurable criteria.\n\n"
                "Constraints:\n"
                "- Be accurate and cite only provided information\n"
                "- Use structured output when specified\n\n"
                "Return your response in the requested format."
            )

        if "judge" in last or "score" in last:
            return '{"score": 0.85, "reason": "Response meets most criteria."}'

        if "json" in last:
            return '{"result": "ok", "confidence": 0.9}'

        if "summarize" in last or "summary" in last:
            return (
                "- Main point one\n"
                "- Main point two\n"
                "- Conclusion\n"
            )

        if "positive" in last or "negative" in last or "sentiment" in last:
            return "positive"

        return f"Mock response ({digest}) for the given prompt."

    def stream(self, messages: list[Message], **kwargs: Any):
        response = self.generate(messages, **kwargs)
        yield response.content
