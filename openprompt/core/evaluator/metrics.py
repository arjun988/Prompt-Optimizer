"""Evaluation metrics and test runner."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable

import yaml

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic, render_messages
from openprompt.providers.base import Message, ModelProvider, create_provider


class MetricType(StrEnum):
    EXACT_MATCH = "exact_match"
    REGEX = "regex"
    JSON_SCHEMA = "json_schema"
    CONTAINS = "contains"
    SEMANTIC = "semantic"
    LLM_JUDGE = "llm_judge"
    CUSTOM = "custom"


@dataclass
class TestCase:
    name: str
    input: str
    expected: str | None = None
    metric: MetricType = MetricType.EXACT_MATCH
    pattern: str | None = None
    schema: dict[str, Any] | None = None
    evaluator: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    test: TestCase
    passed: bool
    score: float
    output: str
    message: str = ""


@dataclass
class EvalReport:
    results: list[TestResult] = field(default_factory=list)
    prompt_tokens: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    judge_score: float | None = None

    @property
    def accuracy(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)


def load_test_suite(path: Path | str) -> list[TestCase]:
    """Load tests from YAML file or directory."""
    path = Path(path)
    if path.is_dir():
        tests: list[TestCase] = []
        for file in sorted(path.glob("**/*")):
            if file.suffix in {".yaml", ".yml"} and file.name.startswith(("test", "tests")):
                tests.extend(load_test_suite(file))
            elif file.name == "tests.yaml":
                tests.extend(load_test_suite(file))
        if not tests and (path / "tests.yaml").exists():
            return load_test_suite(path / "tests.yaml")
        return tests

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw_tests = data.get("tests", data if isinstance(data, list) else [])
    cases: list[TestCase] = []

    for index, item in enumerate(raw_tests):
        metric = item.get("metric", "exact_match")
        cases.append(
            TestCase(
                name=item.get("name", f"test_{index + 1}"),
                input=item["input"],
                expected=item.get("expected"),
                metric=MetricType(metric),
                pattern=item.get("pattern"),
                schema=item.get("schema"),
                evaluator=item.get("evaluator"),
                metadata=item.get("metadata", {}),
            )
        )
    return cases


def score_output(
    output: str,
    test: TestCase,
    *,
    judge_provider: ModelProvider | None = None,
    custom_eval_fn: Callable[[str, str | None], float] | None = None,
) -> tuple[float, str]:
    """Score a single model output against a test case."""
    expected = test.expected

    if test.metric == MetricType.EXACT_MATCH:
        if expected is None:
            return (1.0, "No expected value; skipped.") if output.strip() else (0.0, "Empty output.")
        passed = output.strip() == expected.strip()
        return (1.0 if passed else 0.0, "Exact match." if passed else "Output differs from expected.")

    if test.metric == MetricType.CONTAINS:
        if expected is None:
            return 0.0, "Missing expected substring."
        passed = expected.lower() in output.lower()
        return (1.0 if passed else 0.0, "Contains expected." if passed else "Missing expected text.")

    if test.metric == MetricType.REGEX:
        pattern = test.pattern or expected
        if not pattern:
            return 0.0, "Missing regex pattern."
        passed = bool(re.search(pattern, output, re.DOTALL | re.IGNORECASE))
        return (1.0 if passed else 0.0, "Regex matched." if passed else "Regex did not match.")

    if test.metric == MetricType.JSON_SCHEMA:
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError:
            return 0.0, "Output is not valid JSON."
        if test.schema:
            errors = _validate_json_schema(parsed, test.schema)
            if errors:
                return 0.0, "; ".join(errors)
        if expected:
            try:
                expected_json = json.loads(expected)
                if parsed == expected_json:
                    return 1.0, "JSON matches expected."
                return 0.5, "Valid JSON but differs from expected."
            except json.JSONDecodeError:
                pass
        return 1.0, "Valid JSON."

    if test.metric == MetricType.SEMANTIC:
        if expected is None:
            return 0.0, "Missing expected for semantic comparison."
        from openprompt.core.evaluator.semantic import semantic_similarity

        similarity = semantic_similarity(output, expected)
        return similarity, f"Semantic similarity: {similarity:.2f}"

    if test.metric == MetricType.LLM_JUDGE:
        if judge_provider is None:
            return 0.0, "LLM judge provider not configured."
        from openprompt.core.evaluator.judge import judge_response

        score, reason = judge_response(judge_provider, test.input, output, expected, test.metadata)
        return score, reason

    if test.metric == MetricType.CUSTOM:
        if custom_eval_fn is None:
            return 0.0, "Custom evaluator not loaded."
        try:
            score = float(custom_eval_fn(output, expected))
            return max(0.0, min(1.0, score)), "Custom evaluator score."
        except Exception as exc:
            return 0.0, f"Custom evaluator error: {exc}"

    return 0.0, f"Unknown metric: {test.metric}"


def run_evaluation(
    ast: PromptAST,
    tests: list[TestCase],
    provider: ModelProvider,
    *,
    judge_provider: ModelProvider | None = None,
    custom_eval_fn: Callable[[str, str | None], float] | None = None,
    provider_name: str = "mock",
    model_name: str | None = None,
) -> EvalReport:
    """Run all test cases against a prompt AST."""
    from openprompt.core.cost.pricing import estimate_cost_usd

    prompt_text = render_generic(ast)
    prompt_tokens = max(1, len(prompt_text) // 4)
    results: list[TestResult] = []
    total_cost = 0.0
    total_latency = 0.0
    judge_scores: list[float] = []

    for test in tests:
        messages = render_messages(ast)
        user_suffix = f"\n\n---\nInput:\n{test.input}"
        if messages:
            last = messages[-1]
            messages = [*messages[:-1], Message(role=last.role, content=last.content + user_suffix)]
        else:
            from openprompt.providers.base import Message

            messages = [Message(role="user", content=user_suffix.strip())]

        response = provider.generate(messages)
        total_cost += estimate_cost_usd(response, provider=provider_name, model=model_name or getattr(provider, "model", None))
        total_latency += response.latency_ms

        score, message = score_output(
            response.content,
            test,
            judge_provider=judge_provider,
            custom_eval_fn=custom_eval_fn,
        )
        if test.metric == MetricType.LLM_JUDGE:
            judge_scores.append(score)
        results.append(
            TestResult(
                test=test,
                passed=score >= 0.999,
                score=score,
                output=response.content,
                message=message,
            )
        )

    return EvalReport(
        results=results,
        prompt_tokens=prompt_tokens,
        total_cost_usd=total_cost,
        total_latency_ms=total_latency,
        judge_score=(sum(judge_scores) / len(judge_scores)) if judge_scores else None,
    )


def resolve_prompt_in_directory(directory: Path) -> Path | None:
    """Resolve the primary prompt file inside a task directory."""
    if not directory.is_dir():
        return None
    for name in ("prompt.txt", "prompt.yaml", "prompt.yml", "prompt.md"):
        candidate = directory / name
        if candidate.exists():
            return candidate
    for pattern in ("*.yaml", "*.yml", "*.txt", "*.md"):
        matches = sorted(directory.glob(pattern))
        matches = [m for m in matches if m.name != "tests.yaml"]
        if matches:
            return matches[0]
    return None


def resolve_test_suite(prompt_path: Path) -> Path | None:
    """Find tests.yaml for a prompt file or task directory."""
    if prompt_path.is_dir():
        candidate = prompt_path / "tests.yaml"
        return candidate if candidate.exists() else None

    candidates = [
        prompt_path.parent / "tests.yaml",
        prompt_path.parent / prompt_path.stem / "tests.yaml",
        prompt_path.with_suffix(".tests.yaml"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _validate_json_schema(data: Any, schema: dict[str, Any]) -> list[str]:
    """Minimal JSON schema validation without jsonschema dependency."""
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(data, dict):
        errors.append("Expected JSON object.")
    elif expected_type == "array" and not isinstance(data, list):
        errors.append("Expected JSON array.")
    elif expected_type == "string" and not isinstance(data, str):
        errors.append("Expected JSON string.")

    required = schema.get("required", [])
    if isinstance(data, dict):
        for key in required:
            if key not in data:
                errors.append(f"Missing required field: {key}")

    properties = schema.get("properties", {})
    if isinstance(data, dict):
        for key, spec in properties.items():
            if key in data and "type" in spec:
                if spec["type"] == "string" and not isinstance(data[key], str):
                    errors.append(f"Field {key} must be string.")
                if spec["type"] == "number" and not isinstance(data[key], (int, float)):
                    errors.append(f"Field {key} must be number.")

    return errors
