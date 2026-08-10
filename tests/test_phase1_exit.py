from pathlib import Path

from openprompt.core.evaluator.metrics import load_test_suite, resolve_prompt_in_directory, run_evaluation
from openprompt.core.parser.parser import parse_file
from openprompt.providers.mock import MockProvider


def test_phase1_eval_directory_target(examples_dir: Path, mock_provider: MockProvider) -> None:
    task_dir = examples_dir / "summarize"
    prompt = resolve_prompt_in_directory(task_dir)
    assert prompt is not None
    ast = parse_file(prompt)
    tests = load_test_suite(task_dir / "tests.yaml")
    report = run_evaluation(ast, tests, mock_provider, provider_name="mock")
    assert report.accuracy >= 0


def test_phase1_inspect_and_lint(examples_dir: Path) -> None:
    from openprompt.core.linter.linter import lint

    ast = parse_file(examples_dir / "code-review.yaml")
    report = lint(ast)
    assert report.score > 0
