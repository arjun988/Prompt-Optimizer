"""Provider-specific token pricing for cost-aware optimization."""

from __future__ import annotations

from dataclasses import dataclass

from openprompt.providers.base import ModelResponse


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


# USD per 1M tokens (approximate; Aug 2026 — update as providers change pricing)
PRICING_TABLE: dict[str, ModelPricing] = {
    # OpenAI GPT-5.6
    "gpt-5.6-sol": ModelPricing(5.00, 20.00),
    "gpt-5.6-terra": ModelPricing(2.00, 12.00),
    "gpt-5.6-luna": ModelPricing(0.20, 1.20),
    "gpt-5.6": ModelPricing(5.00, 20.00),
    "gpt-5.5": ModelPricing(4.00, 16.00),
    "gpt-5.4": ModelPricing(3.50, 14.00),
    "gpt-5.4-mini": ModelPricing(0.80, 3.20),
    "gpt-5.4-nano": ModelPricing(0.20, 0.80),
    "gpt-5.1": ModelPricing(3.00, 12.00),
    "gpt-5-mini": ModelPricing(0.50, 2.00),
    "gpt-5-nano": ModelPricing(0.15, 0.60),
    # OpenAI GPT-4.x / o-series
    "gpt-4.1": ModelPricing(2.00, 8.00),
    "gpt-4.1-mini": ModelPricing(0.40, 1.60),
    "gpt-4.1-nano": ModelPricing(0.10, 0.40),
    "gpt-4o": ModelPricing(2.50, 10.00),
    "gpt-4o-mini": ModelPricing(0.15, 0.60),
    "o3-mini": ModelPricing(1.10, 4.40),
    # Anthropic Claude 5 / 4.x
    "claude-opus-5": ModelPricing(15.00, 75.00),
    "claude-sonnet-5": ModelPricing(3.00, 15.00),
    "claude-fable-5": ModelPricing(5.00, 25.00),
    "claude-opus-4-8": ModelPricing(12.00, 60.00),
    "claude-opus-4-7": ModelPricing(10.00, 50.00),
    "claude-opus-4-6": ModelPricing(8.00, 40.00),
    "claude-sonnet-4-6": ModelPricing(3.00, 15.00),
    "claude-sonnet-4-5": ModelPricing(3.00, 15.00),
    "claude-haiku-4-5": ModelPricing(0.80, 4.00),
    # Gemini
    "gemini-3.6-flash": ModelPricing(0.20, 0.80),
    "gemini-3.5-flash": ModelPricing(0.18, 0.72),
    "gemini-3.5-flash-lite": ModelPricing(0.08, 0.32),
    "gemini-3.1-pro": ModelPricing(1.50, 6.00),
    "gemini-3-flash": ModelPricing(0.20, 0.80),
    "gemini-2.5-pro": ModelPricing(1.25, 5.00),
    "gemini-2.5-flash": ModelPricing(0.15, 0.60),
    "gemini-2.5-flash-lite": ModelPricing(0.08, 0.30),
    "gemini-2.0-flash": ModelPricing(0.10, 0.40),
    "gemini-2.0-flash-lite": ModelPricing(0.05, 0.20),
    # Grok (xAI)
    "grok-4.5": ModelPricing(2.00, 10.00),
    "grok-4.3": ModelPricing(1.25, 2.50),
    "grok-4.20": ModelPricing(1.25, 2.50),
    # Local / mock
    "llama3.3": ModelPricing(0.0, 0.0),
    "llama3.2": ModelPricing(0.0, 0.0),
    "mock-model": ModelPricing(0.0, 0.0),
}

PROVIDER_DEFAULTS: dict[str, ModelPricing] = {
    "openai": ModelPricing(2.00, 12.00),
    "anthropic": ModelPricing(3.00, 15.00),
    "gemini": ModelPricing(0.15, 0.60),
    "grok": ModelPricing(1.25, 2.50),
    "ollama": ModelPricing(0.0, 0.0),
    "mock": ModelPricing(0.0, 0.0),
    "openrouter": ModelPricing(2.00, 10.00),
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
        normalized = model.lower()
        # Longest-prefix match for versioned IDs (e.g. grok-4.20-0309-reasoning)
        best_key = ""
        best_pricing: ModelPricing | None = None
        for key, pricing in PRICING_TABLE.items():
            if key in normalized and len(key) > len(best_key):
                best_key = key
                best_pricing = pricing
        if best_pricing:
            return best_pricing
    return PROVIDER_DEFAULTS.get(provider, ModelPricing(1.0, 3.0))
