"""Main Optimizer API — thin wrapper around OpenPrompt SDK."""

from __future__ import annotations

from pathlib import Path

from openprompt.config.models import ProjectConfig, find_project_config
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.providers.base import create_provider
from openprompt.sdk.client import OpenPrompt


class Optimizer:
    """High-level SDK for prompt optimization (delegates to OpenPrompt)."""

    def __init__(
        self,
        provider: str = "mock",
        model: str = "mock-model",
        *,
        config: ProjectConfig | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        warn_mock: bool = True,
    ) -> None:
        self._client = OpenPrompt(
            provider=provider,
            model=model,
            config=config,
            api_key=api_key,
            base_url=base_url,
            warn_mock=warn_mock,
        )
        self.config = self._client.config
        self.provider = create_provider(
            self.config.model.provider,
            self.config.model.name,
            api_key=api_key or self.config.model.api_key,
            base_url=base_url or self.config.model.base_url,
            warn_mock=warn_mock,
        )

    def optimize(
        self,
        prompt: str | Path,
        *,
        strategy: str | None = None,
        tests_path: str | Path | None = None,
        objective: str | None = None,
        constraints: dict | None = None,
    ) -> OptimizeResult:
        return self._client.optimize(
            prompt,
            strategy=strategy,
            tests_path=tests_path,
            objective=objective,
            constraints=constraints,
        )
