"""Benchmark multiple prompts and generate reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.core.evaluator.metrics import EvalReport, TestCase, run_evaluation
from openprompt.core.linter.linter import lint
from openprompt.core.parser.parser import parse_file
from openprompt.providers.base import ModelProvider


@dataclass
class BenchmarkEntry:
    name: str
    path: str
    lint_score: int
    eval_score: float
    tokens: int
    pass_rate: float


@dataclass
class BenchmarkReport:
    entries: list[BenchmarkEntry] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_markdown(self) -> str:
        lines = [
            "# OpenPrompt Benchmark Report",
            "",
            f"Generated: {self.generated_at}",
            "",
            "| Prompt | Lint | Eval | Tokens | Pass Rate |",
            "|--------|------|------|--------|-----------|",
        ]
        for entry in sorted(self.entries, key=lambda e: -e.eval_score):
            lines.append(
                f"| {entry.name} | {entry.lint_score} | {entry.eval_score:.1%} | "
                f"{entry.tokens} | {entry.pass_rate:.1%} |"
            )
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(
            {
                "generated_at": self.generated_at,
                "entries": [e.__dict__ for e in self.entries],
            },
            indent=2,
        )


def benchmark_paths(
    paths: list[Path],
    provider: ModelProvider,
    tests: list[TestCase] | None = None,
    *,
    tests_dir: Path | None = None,
) -> BenchmarkReport:
    report = BenchmarkReport()
    for path in paths:
        ast = parse_file(path)
        lint_report = lint(ast)
        tokens = max(1, len(render_generic(ast)) // 4)

        eval_score = 0.0
        pass_rate = 0.0
        suite = tests
        if tests_dir and (tests_dir / path.stem / "tests.yaml").exists():
            from openprompt.core.evaluator.metrics import load_test_suite

            suite = load_test_suite(tests_dir / path.stem / "tests.yaml")
        elif path.parent / "tests.yaml" == path or (path.parent / "tests.yaml").exists():
            from openprompt.core.evaluator.metrics import load_test_suite

            candidate = path.parent / "tests.yaml"
            if candidate.exists() and path.is_file():
                suite = load_test_suite(candidate)

        if suite:
            eval_report = run_evaluation(ast, suite, provider)
            eval_score = eval_report.accuracy
            pass_rate = eval_report.pass_rate
        else:
            eval_score = lint_report.score / 100.0
            pass_rate = eval_score

        report.entries.append(
            BenchmarkEntry(
                name=path.stem,
                path=str(path),
                lint_score=lint_report.score,
                eval_score=eval_score,
                tokens=tokens,
                pass_rate=pass_rate,
            )
        )
    return report


def compare_prompts(
    prompt_a: PromptAST,
    prompt_b: PromptAST,
    provider: ModelProvider,
    tests: list[TestCase],
) -> dict:
    eval_a = run_evaluation(prompt_a, tests, provider)
    eval_b = run_evaluation(prompt_b, tests, provider)
    return {
        "a": {"accuracy": eval_a.accuracy, "tokens": eval_a.prompt_tokens},
        "b": {"accuracy": eval_b.accuracy, "tokens": eval_b.prompt_tokens},
        "delta_accuracy": eval_b.accuracy - eval_a.accuracy,
        "delta_tokens": eval_b.prompt_tokens - eval_a.prompt_tokens,
    }
