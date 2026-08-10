"""Resolve provider credentials from args and environment."""

from __future__ import annotations

import os

from openprompt.config.models import EnvSettings


def resolve_api_key(provider: str, api_key: str | None = None) -> str | None:
    if api_key:
        return api_key
    env = EnvSettings()
    mapping = {
        "openai": env.openai_api_key or os.environ.get("OPENAI_API_KEY"),
        "anthropic": env.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"),
        "openrouter": env.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY"),
        "grok": env.xai_api_key or os.environ.get("XAI_API_KEY"),
        "gemini": env.google_api_key or env.gemini_api_key or os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"),
    }
    return mapping.get(provider)


def resolve_base_url(provider: str, base_url: str | None = None) -> str | None:
    if base_url:
        return base_url
    if provider == "ollama":
        return os.environ.get("OLLAMA_HOST")
    if provider == "grok":
        return os.environ.get("XAI_BASE_URL")
    if provider == "openrouter":
        return os.environ.get("OPENROUTER_BASE_URL")
    return None
