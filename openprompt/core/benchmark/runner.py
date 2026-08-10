"""Benchmark multiple prompts and generate reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.core.cost.pricing import estimate_tokens_cost_usd
from openprompt.core.evaluator.metrics import (
    EvalReport,
    TestCase,
    load_test_suite,
    resolve_prompt_in_directory,
    resolve_test_suite,
    run_evaluation,
)
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
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    judge_score: float | None = None


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
            "| Prompt | Lint | Eval | Judge | Tokens | Cost (USD) | Latency (ms) | Pass Rate |",
            "|--------|------|------|-------|--------|------------|--------------|-----------|",
        ]
        for entry in sorted(self.entries, key=lambda e: -e.eval_score):
            judge = f"{entry.judge_score:.1%}" if entry.judge_score is not None else "—"
            lines.append(
                f"| {entry.name} | {entry.lint_score} | {entry.eval_score:.1%} | {judge} | "
                f"{entry.tokens} | ${entry.cost_usd:.4f} | {entry.latency_ms:.0f} | {entry.pass_rate:.1%} |"
            )
        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(
            {"generated_at": self.generated_at, "entries": [e.__dict__ for e in self.entries]},
            indent=2,
        )


def benchmark_paths(
    paths: list[Path],
    provider: ModelProvider,
    tests: list[TestCase] | None = None,
    *,
    tests_dir: Path | None = None,
    provider_name: str = "mock",
    model_name: str | None = None,
    judge_provider: ModelProvider | None = None,
) -> BenchmarkReport:
    report = BenchmarkReport()
    for path in paths:
        ast = parse_file(path)
        lint_report = lint(ast)
        tokens = max(1, len(render_generic(ast)) // 4)

        suite = tests or _resolve_suite_for_path(path, tests_dir)
        eval_score = lint_report.score / 100.0
        pass_rate = eval_score
        cost_usd = estimate_tokens_cost_usd(tokens, tokens // 3, provider=provider_name, model=model_name)
        latency_ms = 0.0
        judge_score = None

        if suite:
            eval_report = run_evaluation(
                ast,
                suite,
                provider,
                judge_provider=judge_provider,
                provider_name=provider_name,
                model_name=model_name,
            )
            eval_score = eval_report.accuracy
            pass_rate = eval_report.pass_rate
            cost_usd = eval_report.total_cost_usd
            latency_ms = eval_report.total_latency_ms
            judge_score = eval_report.judge_score

        report.entries.append(
            BenchmarkEntry(
                name=path.stem,
                path=str(path),
                lint_score=lint_report.score,
                eval_score=eval_score,
                tokens=tokens,
                pass_rate=pass_rate,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                judge_score=judge_score,
            )
        )
    return report


def compare_prompts(
    prompt_a: PromptAST,
    prompt_b: PromptAST,
    provider: ModelProvider,
    tests: list[TestCase],
    *,
    provider_name: str = "mock",
    model_name: str | None = None,
) -> dict:
    eval_a = run_evaluation(prompt_a, tests, provider, provider_name=provider_name, model_name=model_name)
    eval_b = run_evaluation(prompt_b, tests, provider, provider_name=provider_name, model_name=model_name)
    return {
        "a": {
            "accuracy": eval_a.accuracy,
            "tokens": eval_a.prompt_tokens,
            "cost_usd": eval_a.total_cost_usd,
            "latency_ms": eval_a.total_latency_ms,
        },
        "b": {
            "accuracy": eval_b.accuracy,
            "tokens": eval_b.prompt_tokens,
            "cost_usd": eval_b.total_cost_usd,
            "latency_ms": eval_b.total_latency_ms,
        },
        "delta_accuracy": eval_b.accuracy - eval_a.accuracy,
        "delta_tokens": eval_b.prompt_tokens - eval_a.prompt_tokens,
        "delta_cost_usd": eval_b.total_cost_usd - eval_a.total_cost_usd,
    }


def _resolve_suite_for_path(path: Path, tests_dir: Path | None) -> list[TestCase] | None:
    if tests_dir and (tests_dir / path.stem / "tests.yaml").exists():
        return load_test_suite(tests_dir / path.stem / "tests.yaml")
    resolved = resolve_test_suite(path if path.is_dir() else path)
    if resolved:
        return load_test_suite(resolved)
    if path.is_dir():
        prompt = resolve_prompt_in_directory(path)
        if prompt:
            resolved = resolve_test_suite(path)
            if resolved:
                return load_test_suite(resolved)
    return None
