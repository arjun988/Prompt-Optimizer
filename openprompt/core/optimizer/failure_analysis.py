"""Analyze evaluation failures and recommend mutations."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from openprompt.core.evaluator.metrics import TestResult


@dataclass
class FailureAnalysis:
    test_name: str
    category: str
    observed: str
    expected: str | None
    recommended_operator: str
    recommendation: str


FAILURE_RULES: list[tuple[str, str, str, str]] = [
    (r"json|JSON|schema", "missing_output_schema", "output", "Add strict JSON schema and format constraint."),
    (r"regex|pattern", "format_mismatch", "output", "Clarify output format with regex or template."),
    (r"exact|differs", "instruction_drift", "constraint", "Add constraints to follow expected format exactly."),
    (r"semantic|similarity", "semantic_gap", "structure", "Decompose task and add verification steps."),
    (r"empty", "empty_output", "constraint", "Require non-empty response with minimum content rules."),
]


def analyze_failures(results: list[TestResult]) -> list[FailureAnalysis]:
    analyses: list[FailureAnalysis] = []
    for result in results:
        if result.passed:
            continue
        analysis = _analyze_single(result)
        if analysis:
            analyses.append(analysis)
    return analyses


def _analyze_single(result: TestResult) -> FailureAnalysis | None:
    message = result.message.lower()
    output_preview = result.output[:200]

    category = "unknown"
    operator = "structure"
    recommendation = "Review failing test and refine prompt."

    for pattern, cat, op, rec in FAILURE_RULES:
        if re.search(pattern, message, re.IGNORECASE):
            category = cat
            operator = op
            recommendation = rec
            break

    if result.test.metric.value == "json_schema" or "json" in message:
        category = "missing_output_schema"
        operator = "output"
        recommendation = "Add strict JSON schema via OutputMutation."

    if not result.output.strip():
        category = "empty_output"
        operator = "constraint"

    expected = result.test.expected
    if expected and _looks_like_json(expected) and not _looks_like_json(result.output):
        category = "format_mismatch"
        operator = "output"
        recommendation = "Model returned non-JSON; enforce JSON-only output."

    return FailureAnalysis(
        test_name=result.test.name,
        category=category,
        observed=output_preview,
        expected=expected[:200] if expected else None,
        recommended_operator=operator,
        recommendation=recommendation,
    )


def _looks_like_json(text: str) -> bool:
    text = text.strip()
    if not text.startswith(("{", "[")):
        return False
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False
