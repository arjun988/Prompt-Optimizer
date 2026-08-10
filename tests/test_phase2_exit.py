from pathlib import Path

from openprompt import Optimizer
from openprompt.config.models import OptimizerConfig, ProjectConfig
from openprompt.core.evaluator.metrics import load_test_suite, run_evaluation
from openprompt.core.linter.linter import lint
from openprompt.core.parser.parser import parse_file
from openprompt.providers.mock import MockProvider


def test_phase2_optimized_beats_baseline_eval(benchmarks_dir: Path, mock_provider: MockProvider) -> None:
    tests = load_test_suite(benchmarks_dir / "classification" / "tests.yaml")
    baseline_ast = parse_file(benchmarks_dir / "classification" / "baseline.txt")
    optimized_ast = parse_file(benchmarks_dir / "classification" / "optimized.yaml")

    baseline_eval = run_evaluation(baseline_ast, tests, mock_provider, provider_name="mock").accuracy
    optimized_eval = run_evaluation(optimized_ast, tests, mock_provider, provider_name="mock").accuracy
    assert optimized_eval >= baseline_eval


def test_phase2_token_reduction_or_quality_gain(benchmarks_dir: Path) -> None:
    baseline = parse_file(benchmarks_dir / "summarize" / "baseline.txt")
    optimized = parse_file(benchmarks_dir / "summarize" / "optimized.yaml")
    baseline_tokens = baseline.estimate_tokens()
    optimized_tokens = optimized.estimate_tokens()
    baseline_lint = lint(baseline).score
    optimized_lint = lint(optimized).score

    quality_gain = (optimized_lint - baseline_lint) / max(baseline_lint, 1)
    token_reduction = (baseline_tokens - optimized_tokens) / max(baseline_tokens, 1)
    assert quality_gain >= 0.15 or token_reduction >= 0.20 or optimized_lint > baseline_lint


def test_phase2_hybrid_strategy_runs(examples_dir: Path) -> None:
    config = ProjectConfig(optimizer=OptimizerConfig(strategy="hybrid", eval_budget=6))
    result = Optimizer(provider="mock", config=config).optimize(
        examples_dir / "summarize" / "prompt.txt",
        tests_path=examples_dir / "summarize" / "tests.yaml",
    )
    assert result.optimized_score >= 0
