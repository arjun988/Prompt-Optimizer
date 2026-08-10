"""Main Optimizer API."""

from __future__ import annotations

from pathlib import Path

from openprompt.config.models import ProjectConfig, find_project_config
from openprompt.core.evaluator.custom import load_custom_evaluator
from openprompt.core.evaluator.metrics import (
    load_test_suite,
    resolve_prompt_in_directory,
    resolve_test_suite,
)
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.optimizer.strategies import StrategyContext, run_strategy
from openprompt.core.parser.parser import parse_any, parse_file
from openprompt.providers.base import create_provider


class Optimizer:
    """High-level SDK for prompt optimization."""

    def __init__(
        self,
        provider: str = "mock",
        model: str = "mock-model",
        *,
        config: ProjectConfig | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.config = config or find_project_config()
        if provider != "mock":
            self.config.model.provider = provider
            self.config.model.name = model
        self.provider = create_provider(
            self.config.model.provider,
            self.config.model.name,
            api_key=api_key or self.config.model.api_key,
            base_url=base_url or self.config.model.base_url,
        )
        self._judge_provider = None
        if self.config.evaluation.judge:
            j = self.config.evaluation.judge
            self._judge_provider = create_provider(j.provider, j.model)

    def optimize(
        self,
        prompt: str | Path,
        *,
        strategy: str | None = None,
        tests_path: str | Path | None = None,
        objective: str | None = None,
        constraints: dict | None = None,
    ) -> OptimizeResult:
        if objective == "maximize_accuracy":
            self.config.objectives.quality_weight = 1.5
        if constraints:
            if "max_tokens" in constraints:
                self.config.objectives.token_weight = 0.5

        if isinstance(prompt, Path) or (isinstance(prompt, str) and Path(prompt).exists()):
            path = Path(prompt)
            if path.is_dir():
                prompt_file = resolve_prompt_in_directory(path)
                if not prompt_file:
                    raise FileNotFoundError(f"No prompt file found in directory: {path}")
                ast = parse_file(prompt_file)
            else:
                ast = parse_file(path)
        else:
            ast = parse_any(str(prompt))

        tests = None
        if tests_path:
            tests = load_test_suite(tests_path)
        elif isinstance(prompt, (str, Path)) and Path(prompt).exists():
            path = Path(prompt)
            resolved = resolve_test_suite(path)
            if resolved:
                tests = load_test_suite(resolved)

        custom_eval_fn = None
        if self.config.evaluation.custom_evaluator:
            custom_eval_fn = load_custom_evaluator(self.config.evaluation.custom_evaluator)

        strategy_name = strategy or self.config.optimizer.strategy
        ctx = StrategyContext(
            provider=self.provider,
            judge_provider=self._judge_provider,
            tests=tests,
            config=self.config,
            custom_eval_fn=custom_eval_fn,
        )
        return run_strategy(ast, strategy_name, ctx)
