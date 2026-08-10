"""Model provider protocol and factory."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass
class ModelResponse:
    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def estimated_cost_usd(self, input_price_per_m: float = 2.5, output_price_per_m: float = 10.0) -> float:
        return (self.input_tokens * input_price_per_m + self.output_tokens * output_price_per_m) / 1_000_000


class ModelProvider(Protocol):
    name: str
    model: str

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse: ...


def create_provider(
    provider: str,
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> ModelProvider:
    """Instantiate a provider by name."""
    if provider == "mock":
        from openprompt.providers.mock import MockProvider

        return MockProvider(model=model)
    if provider == "openai":
        from openprompt.providers.openai_provider import OpenAIProvider

        return OpenAIProvider(model=model, api_key=api_key, base_url=base_url)
    if provider == "anthropic":
        from openprompt.providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(model=model, api_key=api_key)
    if provider == "ollama":
        from openprompt.providers.ollama_provider import OllamaProvider

        return OllamaProvider(model=model, base_url=base_url)
    if provider == "grok":
        from openprompt.providers.grok_provider import GrokProvider

        return GrokProvider(model=model, api_key=api_key, base_url=base_url)
    if provider == "gemini":
        from openprompt.providers.gemini_provider import GeminiProvider

        return GeminiProvider(model=model, api_key=api_key)
    raise ValueError(
        f"Unknown provider: {provider!r}. "
        "Supported: mock, openai, anthropic, ollama, grok, gemini"
    )
