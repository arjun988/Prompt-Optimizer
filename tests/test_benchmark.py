from pathlib import Path

from openprompt.core.benchmark.runner import benchmark_paths
from openprompt.core.parser.parser import parse_file
from openprompt.providers.mock import MockProvider


def test_benchmark_includes_cost_and_judge_columns(benchmarks_dir: Path, mock_provider: MockProvider) -> None:
    paths = [
        benchmarks_dir / "summarize" / "baseline.txt",
        benchmarks_dir / "summarize" / "optimized.yaml",
    ]
    report = benchmark_paths(paths, mock_provider, tests_dir=benchmarks_dir, provider_name="mock")
    md = report.to_markdown()
    assert "Cost (USD)" in md
    assert len(report.entries) == 2


def test_optimized_beats_baseline_lint(benchmarks_dir: Path) -> None:
    from openprompt.core.linter.linter import lint

    baseline = lint(parse_file(benchmarks_dir / "summarize" / "baseline.txt")).score
    optimized = lint(parse_file(benchmarks_dir / "summarize" / "optimized.yaml")).score
    assert optimized > baseline
