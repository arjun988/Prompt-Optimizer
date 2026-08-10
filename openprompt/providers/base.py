"""Model provider protocol and factory."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Protocol

from openprompt.providers.credentials import resolve_api_key, resolve_base_url


@dataclass
class MediaPart:
    """Image or PDF attachment for vision models."""

    path: str | None = None
    url: str | None = None
    mime_type: str = "image/png"
    base64_data: str | None = None
    media_type: Literal["image", "pdf"] = "image"


@dataclass
class Message:
    role: Literal["system", "user", "assistant"]
    content: str
    media: list[MediaPart] = field(default_factory=list)


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


def format_openai_content(message: Message) -> str | list[dict[str, Any]]:
    """Build OpenAI chat content (string or multimodal parts)."""
    if not message.media:
        return message.content
    parts: list[dict[str, Any]] = []
    if message.content.strip():
        parts.append({"type": "text", "text": message.content})
    for item in message.media:
        if item.base64_data:
            url = f"data:{item.mime_type};base64,{item.base64_data}"
        elif item.url:
            url = item.url
        elif item.path:
            from openprompt.core.media.loader import media_to_base64
            from openprompt.core.ast.models import MediaAttachment

            b64, mime = media_to_base64(
                MediaAttachment(path=item.path, mime_type=item.mime_type, media_type=item.media_type)
            )
            url = f"data:{mime};base64,{b64}"
        else:
            continue
        parts.append({"type": "image_url", "image_url": {"url": url}})
    return parts if parts else message.content


class ModelProvider(Protocol):
    name: str
    model: str

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse: ...

    def stream(self, messages: list[Message], **kwargs: Any) -> Iterator[str]: ...


CLOUD_PROVIDERS = {"openai", "anthropic", "ollama", "grok", "gemini", "openrouter"}


def create_provider(
    provider: str,
    model: str,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    resilient: bool = True,
    warn_mock: bool = True,
) -> ModelProvider:
    """Instantiate a provider by name with env credentials and optional retry wrapper."""
    resolved_key = resolve_api_key(provider, api_key)
    resolved_base = resolve_base_url(provider, base_url)

    if provider == "mock":
        from openprompt.providers.mock import MockProvider

        inner = MockProvider(model=model)
        if warn_mock:
            warnings.warn(
                "Using mock provider — optimization scores are heuristic only. "
                "Configure a real provider (openai, anthropic, ollama, etc.) for meaningful results.",
                stacklevel=2,
            )
        return inner

    if provider == "openai":
        from openprompt.providers.openai_provider import OpenAIProvider

        inner = OpenAIProvider(model=model, api_key=resolved_key, base_url=resolved_base)
    elif provider == "anthropic":
        from openprompt.providers.anthropic_provider import AnthropicProvider

        inner = AnthropicProvider(model=model, api_key=resolved_key)
    elif provider == "ollama":
        from openprompt.providers.ollama_provider import OllamaProvider

        inner = OllamaProvider(model=model, base_url=resolved_base)
    elif provider == "grok":
        from openprompt.providers.grok_provider import GrokProvider

        inner = GrokProvider(model=model, api_key=resolved_key, base_url=resolved_base)
    elif provider == "gemini":
        from openprompt.providers.gemini_provider import GeminiProvider

        inner = GeminiProvider(model=model, api_key=resolved_key)
    elif provider == "openrouter":
        from openprompt.providers.openrouter_provider import OpenRouterProvider

        inner = OpenRouterProvider(model=model, api_key=resolved_key, base_url=resolved_base)
    else:
        raise ValueError(
            f"Unknown provider: {provider!r}. "
            "Supported: mock, openai, anthropic, ollama, grok, gemini, openrouter"
        )

    if resilient and provider in CLOUD_PROVIDERS:
        from openprompt.providers.resilient import ResilientProvider

        return ResilientProvider(inner)
    return inner
