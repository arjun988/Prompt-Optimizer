"""Curated provider model IDs for CLI, SDK defaults, and cost estimation.

Updated for Aug 2026 API catalogs. Aliases (e.g. gpt-5.6, gemini-flash-latest) are
included where providers document them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderCatalog:
    id: str
    label: str
    default_model: str
    models: tuple[str, ...]


PROVIDER_CATALOG: tuple[ProviderCatalog, ...] = (
    ProviderCatalog(
        id="mock",
        label="Mock (offline)",
        default_model="mock-model",
        models=("mock-model",),
    ),
    ProviderCatalog(
        id="openai",
        label="OpenAI",
        default_model="gpt-5.6-terra",
        models=(
            "gpt-5.6",
            "gpt-5.6-sol",
            "gpt-5.6-terra",
            "gpt-5.6-luna",
            "gpt-5.5",
            "gpt-5.4",
            "gpt-5.4-mini",
            "gpt-5.4-nano",
            "gpt-5.1",
            "gpt-5-mini",
            "gpt-5-nano",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
            "o3-mini",
        ),
    ),
    ProviderCatalog(
        id="anthropic",
        label="Anthropic",
        default_model="claude-sonnet-5",
        models=(
            "claude-opus-5",
            "claude-sonnet-5",
            "claude-fable-5",
            "claude-opus-4-8",
            "claude-opus-4-7",
            "claude-opus-4-6",
            "claude-opus-4-5",
            "claude-sonnet-4-6",
            "claude-sonnet-4-5",
            "claude-haiku-4-5",
        ),
    ),
    ProviderCatalog(
        id="gemini",
        label="Gemini",
        default_model="gemini-3.6-flash",
        models=(
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-pro-preview",
            "gemini-3-flash-preview",
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-flash-latest",
            "gemini-pro-latest",
        ),
    ),
    ProviderCatalog(
        id="grok",
        label="Grok (xAI)",
        default_model="grok-4.3",
        models=(
            "grok-4.5",
            "grok-4.3",
            "grok-4.20-0309-reasoning",
            "grok-4.20-0309-non-reasoning",
        ),
    ),
    ProviderCatalog(
        id="ollama",
        label="Ollama (local)",
        default_model="llama3.3",
        models=(
            "llama3.3",
            "llama3.2",
            "llama3.1",
            "qwen3",
            "qwen2.5",
            "mistral",
            "gemma3",
            "deepseek-r1",
            "phi4",
        ),
    ),
    ProviderCatalog(
        id="openrouter",
        label="OpenRouter",
        default_model="openai/gpt-5.6-terra",
        models=(
            "openai/gpt-5.6-sol",
            "openai/gpt-5.6-terra",
            "openai/gpt-5.6-luna",
            "openai/gpt-4.1-mini",
            "anthropic/claude-opus-5",
            "anthropic/claude-sonnet-5",
            "google/gemini-3.6-flash",
            "google/gemini-2.5-pro",
            "google/gemini-2.5-flash",
            "x-ai/grok-4.3",
        ),
    ),
)


def catalog_for_provider(provider: str) -> ProviderCatalog | None:
    for entry in PROVIDER_CATALOG:
        if entry.id == provider:
            return entry
    return None


def default_model_for(provider: str) -> str:
    entry = catalog_for_provider(provider)
    return entry.default_model if entry else "mock-model"
