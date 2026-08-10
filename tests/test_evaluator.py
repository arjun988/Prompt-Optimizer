from pathlib import Path

from openprompt.core.evaluator.metrics import (
    MetricType,
    load_test_suite,
    resolve_prompt_in_directory,
    resolve_test_suite,
    run_evaluation,
    score_output,
)
from openprompt.core.parser.parser import parse_file
from openprompt.providers.mock import MockProvider


def test_score_exact_match() -> None:
    score, _ = score_output("positive", _case("positive", MetricType.EXACT_MATCH))
    assert score == 1.0


def test_run_evaluation_examples(examples_dir: Path, mock_provider: MockProvider) -> None:
    prompt = examples_dir / "summarize" / "prompt.txt"
    tests = load_test_suite(examples_dir / "summarize" / "tests.yaml")
    ast = parse_file(prompt)
    report = run_evaluation(ast, tests, mock_provider, provider_name="mock", model_name="mock-model")
    assert len(report.results) == 3
    assert report.total_cost_usd >= 0
    assert report.prompt_tokens > 0


def test_resolve_directory_prompt(examples_dir: Path) -> None:
    task = examples_dir / "summarize"
    assert resolve_prompt_in_directory(task)
    assert resolve_test_suite(task)


def _case(expected: str, metric: MetricType):
    from openprompt.core.evaluator.metrics import TestCase

    return TestCase(name="t", input="x", expected=expected, metric=metric)
