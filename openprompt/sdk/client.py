"""Stable public SDK for OpenPrompt."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openprompt.config.models import ProjectConfig, find_project_config
from openprompt.core.benchmark.runner import BenchmarkReport, benchmark_paths
from openprompt.core.evaluator.custom import load_custom_evaluator
from openprompt.core.evaluator.metrics import (
    EvalReport,
    load_test_suite,
    resolve_prompt_in_directory,
    resolve_test_suite,
    run_evaluation,
)
from openprompt.core.linter.linter import LintReport, lint
from openprompt.core.optimizer.cost_optimizer import CostRecommendation, recommend_cost_quality
from openprompt.core.optimizer.engine import Optimizer
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.optimizer.multi_model import (
    ModelSpec,
    MultiModelOptimizeResult,
    multi_model_optimize,
)
from openprompt.core.parser.parser import parse_any, parse_file
from openprompt.core.security.scanner import SecurityReport, scan
from openprompt.plugins.discovery import discover_evaluators
from openprompt.providers.base import create_provider


@dataclass
class OpenPrompt:
    """
    Stable high-level SDK facade.

    Example::

        from openprompt import OpenPrompt

        client = OpenPrompt(provider="mock")
        report = client.lint("Summarize this article.")
        result = client.optimize("Summarize this article.", strategy="hybrid")
    """

    provider: str = "mock"
    model: str = "mock-model"
    config: ProjectConfig | None = None
    api_key: str | None = None
    base_url: str | None = None

    def __post_init__(self) -> None:
        if self.config is None:
            self.config = find_project_config()
        self.config.model.provider = self.provider
        self.config.model.name = self.model
        if self.api_key:
            self.config.model.api_key = self.api_key
        if self.base_url:
            self.config.model.base_url = self.base_url

    def _optimizer(self) -> Optimizer:
        return Optimizer(
            provider=self.provider,
            model=self.model,
            config=self.config,
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def _resolve_ast(self, prompt: str | Path):
        if isinstance(prompt, Path) or (isinstance(prompt, str) and Path(prompt).exists()):
            path = Path(prompt)
            if path.is_dir():
                prompt_file = resolve_prompt_in_directory(path)
                if not prompt_file:
                    raise FileNotFoundError(f"No prompt in directory: {path}")
                return parse_file(prompt_file)
            return parse_file(path)
        return parse_any(str(prompt))

    def lint(self, prompt: str | Path) -> LintReport:
        """Analyze prompt quality (offline)."""
        return lint(self._resolve_ast(prompt))

    def security_scan(self, prompt: str | Path) -> SecurityReport:
        """Scan prompt for security issues (offline)."""
        return scan(self._resolve_ast(prompt))

    def optimize(
        self,
        prompt: str | Path,
        *,
        strategy: str | None = None,
        tests_path: str | Path | None = None,
        objective: str | None = None,
        constraints: dict[str, Any] | None = None,
    ) -> OptimizeResult:
        """Optimize a prompt."""
        return self._optimizer().optimize(
            prompt,
            strategy=strategy,
            tests_path=tests_path,
            objective=objective,
            constraints=constraints,
        )

    def compress(self, prompt: str | Path, *, tests_path: str | Path | None = None) -> OptimizeResult:
        """Compress prompt tokens while preserving quality."""
        return self.optimize(prompt, strategy="compress", tests_path=tests_path)

    def evaluate(
        self,
        prompt: str | Path,
        tests: list | Path | str | None = None,
    ) -> EvalReport:
        """Run evaluation test suite against a prompt."""
        ast = self._resolve_ast(prompt)
        suite = self._resolve_tests(prompt, tests)
        provider = create_provider(self.provider, self.model, api_key=self.api_key, base_url=self.base_url)

        judge_provider = None
        if self.config and self.config.evaluation.judge:
            j = self.config.evaluation.judge
            judge_provider = create_provider(j.provider, j.model)

        custom_eval_fn = None
        if self.config and self.config.evaluation.custom_evaluator:
            custom_eval_fn = load_custom_evaluator(self.config.evaluation.custom_evaluator)

        plugin_evaluators = discover_evaluators()
        if not custom_eval_fn and tests and isinstance(tests, str) and tests in plugin_evaluators:
            custom_eval_fn = plugin_evaluators[tests]

        return run_evaluation(
            ast,
            suite,
            provider,
            judge_provider=judge_provider,
            custom_eval_fn=custom_eval_fn,
            provider_name=self.provider,
            model_name=self.model,
        )

    def benchmark(
        self,
        paths: list[str | Path],
        *,
        tests_dir: str | Path | None = None,
    ) -> BenchmarkReport:
        """Benchmark multiple prompts."""
        provider = create_provider(self.provider, self.model, api_key=self.api_key, base_url=self.base_url)
        judge_provider = None
        if self.config and self.config.evaluation.judge:
            j = self.config.evaluation.judge
            judge_provider = create_provider(j.provider, j.model)

        return benchmark_paths(
            [Path(p) for p in paths],
            provider,
            tests_dir=Path(tests_dir) if tests_dir else None,
            provider_name=self.provider,
            model_name=self.model,
            judge_provider=judge_provider,
        )

    def multi_model_optimize(
        self,
        prompt: str | Path,
        models: list[ModelSpec | dict[str, str] | str],
        *,
        strategy: str | None = None,
        tests_path: str | Path | None = None,
    ) -> MultiModelOptimizeResult:
        """
        Optimize the same prompt across multiple provider/model pairs.

        ``models`` accepts:
          - ``ModelSpec(provider=\"openai\", model=\"gpt-4o-mini\")``
          - ``{\"provider\": \"ollama\", \"model\": \"llama3.2\"}``
          - ``\"openai:gpt-4o-mini\"`` strings
        """
        normalized = [_coerce_model_spec(m) for m in models]
        return multi_model_optimize(
            prompt,
            normalized,
            config=self.config,
            strategy=strategy,
            tests_path=tests_path,
            api_key=self.api_key,
            base_url=self.base_url,
        )

    def recommend_cost_quality(
        self,
        result: OptimizeResult,
        *,
        min_quality: float | None = None,
    ) -> CostRecommendation:
        """Recommend best quality/cost tradeoff from optimization candidates."""
        return recommend_cost_quality(result, min_quality=min_quality)

    def _resolve_tests(self, prompt: str | Path, tests: list | Path | str | None):
        if isinstance(tests, list):
            return tests
        if tests is not None:
            return load_test_suite(tests)
        if isinstance(prompt, (str, Path)) and Path(prompt).exists():
            path = Path(prompt)
            resolved = resolve_test_suite(path if path.is_dir() else path)
            if resolved:
                return load_test_suite(resolved)
        raise ValueError("Test suite required. Pass tests= path or YAML.")


def _coerce_model_spec(value: ModelSpec | dict[str, str] | str) -> ModelSpec:
    if isinstance(value, ModelSpec):
        return value
    if isinstance(value, dict):
        return ModelSpec(provider=value["provider"], model=value["model"])
    if ":" in value:
        provider, model = value.split(":", 1)
        return ModelSpec(provider=provider, model=model)
    raise ValueError(f"Invalid model spec: {value!r}. Use ModelSpec, dict, or 'provider:model'.")
