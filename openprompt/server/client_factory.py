"""Create OpenPrompt SDK clients for REST handlers."""

from __future__ import annotations

from openprompt.sdk.client import OpenPrompt


def openprompt_client(
    provider: str,
    model: str,
    *,
    api_key: str | None = None,
    warn_mock: bool = False,
) -> OpenPrompt:
    return OpenPrompt(
        provider=provider,
        model=model,
        api_key=api_key or None,
        warn_mock=warn_mock,
    )
