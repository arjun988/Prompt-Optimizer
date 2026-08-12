from pathlib import Path

from openprompt import Optimizer
from openprompt.core.linter.linter import lint
from openprompt.core.parser.parser import parse_file


def test_optimizer_rewrite(examples_dir: Path) -> None:
    prompt = examples_dir / "summarize" / "prompt.txt"
    optimizer = Optimizer(provider="mock", model="mock-model")
    result = optimizer.optimize(prompt, strategy="rewrite")
    assert result.optimized_tokens > 0
    assert result.prompt


def test_optimizer_hybrid_with_tests(examples_dir: Path) -> None:
    from openprompt.config.models import ProjectConfig, OptimizerConfig

    config = ProjectConfig(optimizer=OptimizerConfig(strategy="hybrid", eval_budget=8))
    optimizer = Optimizer(provider="mock", model="mock-model", config=config)
    prompt = examples_dir / "summarize" / "prompt.txt"
    result = optimizer.optimize(prompt, strategy="hybrid", tests_path=examples_dir / "summarize" / "tests.yaml")
    assert result.strategy == "hybrid"
    assert len(result.candidates) >= 1


def test_optimizer_reinforcement_with_csv(examples_dir: Path) -> None:
    from openprompt.config.models import ProjectConfig, OptimizerConfig

    config = ProjectConfig(optimizer=OptimizerConfig(strategy="reinforcement", reinforcement_rounds=2))
    optimizer = Optimizer(provider="mock", model="mock-model", config=config)
    prompt = examples_dir / "summarize" / "prompt.txt"
    result = optimizer.optimize(
        prompt,
        strategy="reinforcement",
        tests_path=examples_dir / "summarize" / "tests.csv",
    )
    assert result.strategy == "reinforcement"
    assert result.optimized_score >= result.original_score
    assert any("API calls used" in line for line in result.report_lines)


def test_lint_improves_after_optimize(examples_dir: Path) -> None:
    baseline = parse_file(examples_dir / "summarize" / "prompt.txt")
    baseline_score = lint(baseline).score
    result = Optimizer(provider="mock").optimize(examples_dir / "summarize" / "prompt.txt", strategy="rewrite")
    optimized_score = lint(result.optimized).score
    assert optimized_score >= baseline_score
