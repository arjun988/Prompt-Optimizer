"""Provider-specific token pricing for cost-aware optimization."""

from __future__ import annotations

from dataclasses import dataclass

from openprompt.providers.base import ModelResponse


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


# USD per 1M tokens (approximate; update as providers change pricing)
PRICING_TABLE: dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "gpt-4.1": ModelPricing(2.00, 8.00),
    "gpt-4.1-mini": ModelPricing(0.40, 1.60),
    "claude-sonnet-4-20250514": ModelPricing(3.00, 15.00),
    "claude-3-5-sonnet-20241022": ModelPricing(3.00, 15.00),
    "gemini-2.0-flash": ModelPricing(0.10, 0.40),
    "gemini-2.5-flash": ModelPricing(0.15, 0.60),
    "grok-2-latest": ModelPricing(2.00, 10.00),
    "grok-2": ModelPricing(2.00, 10.00),
    "llama3.2": ModelPricing(0.0, 0.0),
    "mock-model": ModelPricing(0.0, 0.0),
}

PROVIDER_DEFAULTS: dict[str, ModelPricing] = {
    "openai": ModelPricing(2.50, 10.00),
    "anthropic": ModelPricing(3.00, 15.00),
    "gemini": ModelPricing(0.10, 0.40),
    "grok": ModelPricing(2.00, 10.00),
    "ollama": ModelPricing(0.0, 0.0),
    "mock": ModelPricing(0.0, 0.0),
}


def estimate_cost_usd(
    response: ModelResponse,
    *,
    provider: str = "mock",
    model: str | None = None,
) -> float:
    """Estimate USD cost from token usage."""
    pricing = _resolve_pricing(provider, model)
    return (
        response.input_tokens * pricing.input_per_million
        + response.output_tokens * pricing.output_per_million
    ) / 1_000_000


def estimate_tokens_cost_usd(
    input_tokens: int,
    output_tokens: int,
    *,
    provider: str = "mock",
    model: str | None = None,
) -> float:
    pricing = _resolve_pricing(provider, model)
    return (
        input_tokens * pricing.input_per_million + output_tokens * pricing.output_per_million
    ) / 1_000_000


def _resolve_pricing(provider: str, model: str | None) -> ModelPricing:
    if model:
        for key, pricing in PRICING_TABLE.items():
            if key in model or model in key:
                return pricing
    return PROVIDER_DEFAULTS.get(provider, ModelPricing(1.0, 3.0))
