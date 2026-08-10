"""Rule-based prompt linter and heuristic quality score."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum

from openprompt.core.ast.models import OutputFormat, PromptAST
from openprompt.core.compiler.renderer import render_generic


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    OK = "ok"


@dataclass
class LintIssue:
    code: str
    message: str
    severity: Severity
    recommendation: str | None = None

    @property
    def symbol(self) -> str:
        return {
            Severity.ERROR: "❌",
            Severity.WARNING: "⚠",
            Severity.INFO: "ℹ",
            Severity.OK: "✓",
        }[self.severity]


@dataclass
class LintReport:
    issues: list[LintIssue] = field(default_factory=list)
    score: int = 0
    categories: dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]


# Fix typo in LintReport.errors property - I wrote "self issues" instead of "self.issues"
# I'll fix when writing

AMBIGUOUS_PHRASES = [
    r"\bmake it good\b",
    r"\boptimize this\b",
    r"\bexplain properly\b",
    r"\bgive a detailed answer\b",
    r"\bbe helpful\b",
    r"\bimprove this\b",
    r"\banalyze this\b(?!\s+\w+)",  # bare "analyze this" without object
]

VAGUE_VERBS = ["analyze", "explain", "summarize", "fix", "optimize", "review", "tell me"]

CONTRADICTION_PAIRS = [
    (r"\bbe concise\b", r"\bcomprehensive\b.*\bevery detail\b"),
    (r"\breturn json only\b", r"\bexplain.*paragraphs?\b"),
    (r"\bjson only\b", r"\bmarkdown\b"),
    (r"\bdo not hallucinate\b", r"\bif unsure, guess\b"),
    (r"\bshort answer\b", r"\bas long as possible\b"),
]


def lint(ast: PromptAST) -> LintReport:
    """Run all linter rules against a PromptAST."""
    issues: list[LintIssue] = []
    text = _full_prompt_text(ast)

    issues.extend(_check_ambiguity(ast, text))
    issues.extend(_check_output(ast, text))
    issues.extend(_check_context(ast))
    issues.extend(_check_constraints(ast))
    issues.extend(_check_contradictions(text))
    issues.extend(_check_security(ast, text))
    issues.extend(_check_examples(ast))
    issues.extend(_check_role(ast))

    categories = _score_categories(ast, issues)
    score = _compute_score(categories)

    return LintReport(issues=issues, score=score, categories=categories)


def _full_prompt_text(ast: PromptAST) -> str:
    """Rendered text plus raw source when structured parsing dropped lines."""
    text = render_generic(ast)
    if ast.raw_text and ast.raw_text.strip() not in text:
        return f"{text}\n{ast.raw_text}".strip()
    return text


def _check_ambiguity(ast: PromptAST, text: str) -> list[LintIssue]:
    issues: list[LintIssue] = []
    lower = text.lower()

    for pattern in AMBIGUOUS_PHRASES:
        if re.search(pattern, lower):
            issues.append(
                LintIssue(
                    code="ambiguous_objective",
                    message="Ambiguous or subjective phrasing detected.",
                    severity=Severity.ERROR,
                    recommendation="Replace subjective terms with measurable criteria.",
                )
            )
            break

    objective = ast.objective.raw if ast.objective else text.split("\n")[0]
    if objective and len(objective.split()) < 4:
        issues.append(
            LintIssue(
                code="vague_objective",
                message="Objective appears too short or vague.",
                severity=Severity.WARNING,
                recommendation="Add task scope, audience, and success criteria.",
            )
        )

    return issues


def _check_output(ast: PromptAST, text: str) -> list[LintIssue]:
    issues: list[LintIssue] = []

    if not ast.output:
        if not re.search(r"\b(format|return|output|json|markdown)\b", text, re.IGNORECASE):
            issues.append(
                LintIssue(
                    code="missing_output_format",
                    message="No explicit output format or schema.",
                    severity=Severity.WARNING,
                    recommendation="Specify format (JSON, markdown sections, max length).",
                )
            )
    elif ast.output.format == OutputFormat.JSON and not ast.output.schema_:
        issues.append(
            LintIssue(
                code="missing_json_schema",
                message="JSON output requested without schema.",
                severity=Severity.WARNING,
                recommendation="Add a JSON schema or example object.",
            )
        )

    if ast.output and not ast.output.sections and ast.output.format == OutputFormat.MARKDOWN:
        issues.append(
            LintIssue(
                code="missing_output_sections",
                message="Markdown output without defined sections.",
                severity=Severity.INFO,
                recommendation="List required sections (e.g. Key Findings, Recommendations).",
            )
        )

    return issues


def _check_context(ast: PromptAST) -> list[LintIssue]:
    if ast.context:
        return [
            LintIssue(
                code="context_provided",
                message="Context section present.",
                severity=Severity.OK,
            )
        ]

    task = ast.objective.task if ast.objective else None
    if task in {"code_review", "debugging", "extraction"}:
        return [
            LintIssue(
                code="missing_context",
                message=f"Task '{task}' typically needs explicit context placeholders.",
                severity=Severity.WARNING,
                recommendation="Add context fields (source code, error, environment).",
            )
        ]
    return []


def _check_constraints(ast: PromptAST) -> list[LintIssue]:
    issues: list[LintIssue] = []
    if not ast.constraints:
        issues.append(
            LintIssue(
                code="missing_constraints",
                message="No explicit constraints or failure conditions.",
                severity=Severity.WARNING,
                recommendation="Add constraints (accuracy, no hallucination, scope limits).",
            )
        )
    else:
        issues.append(
            LintIssue(
                code="constraints_provided",
                message="Constraints defined.",
                severity=Severity.OK,
            )
        )
    return issues


def _check_contradictions(text: str) -> list[LintIssue]:
    issues: list[LintIssue] = []
    lower = text.lower()
    for pattern_a, pattern_b in CONTRADICTION_PAIRS:
        if re.search(pattern_a, lower) and re.search(pattern_b, lower):
            issues.append(
                LintIssue(
                    code="conflicting_instructions",
                    message="Potentially conflicting instructions detected.",
                    severity=Severity.ERROR,
                    recommendation="Resolve conflict or split into structured output fields.",
                )
            )
    return issues


def _check_security(ast: PromptAST, text: str) -> list[LintIssue]:
    issues: list[LintIssue] = []
    if re.search(r"\b(api[_-]?key|password|secret|token)\s*[:=]", text, re.IGNORECASE):
        issues.append(
            LintIssue(
                code="possible_secret",
                message="Possible secret or credential in prompt text.",
                severity=Severity.ERROR,
                recommendation="Remove secrets; use environment variables.",
            )
        )

    if ast.security and ast.security.untrusted_input_isolation:
        issues.append(
            LintIssue(
                code="untrusted_isolation",
                message="Untrusted input isolation configured.",
                severity=Severity.OK,
            )
        )
    elif re.search(r"\buser.?provided|document|retrieved|context\b", text, re.IGNORECASE):
        issues.append(
            LintIssue(
                code="missing_untrusted_isolation",
                message="Prompt references external content without isolation guidance.",
                severity=Severity.WARNING,
                recommendation="Add security rules for untrusted input.",
            )
        )
    return issues


def _check_examples(ast: PromptAST) -> list[LintIssue]:
    if len(ast.examples) >= 2:
        return [
            LintIssue(
                code="examples_provided",
                message=f"{len(ast.examples)} few-shot examples present.",
                severity=Severity.OK,
            )
        ]
    return []


def _check_role(ast: PromptAST) -> list[LintIssue]:
    if ast.role and ast.role.enabled and ast.role.description:
        return [
            LintIssue(
                code="role_defined",
                message="Role/persona defined.",
                severity=Severity.OK,
            )
        ]
    return []


def _score_categories(ast: PromptAST, issues: list[LintIssue]) -> dict[str, int]:
    """Heuristic sub-scores (each out of 20, security out of 10)."""
    error_codes = {i.code for i in issues if i.severity == Severity.ERROR}
    warning_codes = {i.code for i in issues if i.severity == Severity.WARNING}

    intent = 20
    if "ambiguous_objective" in error_codes or "vague_objective" in warning_codes:
        intent -= 8

    context = 20 if ast.context or "context_provided" in {i.code for i in issues} else 12
    if "missing_context" in warning_codes:
        context -= 6

    constraints = 20 if ast.constraints else 10
    if "missing_constraints" in warning_codes:
        constraints -= 5

    output = 20 if ast.output else 10
    if "missing_output_format" in warning_codes:
        output -= 8
    if "missing_json_schema" in warning_codes:
        output -= 5

    robustness = 20
    if "conflicting_instructions" in error_codes:
        robustness -= 10
    if not ast.verification:
        robustness -= 3

    security = 10
    if "possible_secret" in error_codes:
        security -= 8
    if "missing_untrusted_isolation" in warning_codes:
        security -= 3
    if "untrusted_isolation" in {i.code for i in issues}:
        security = min(10, security + 2)

    return {
        "intent": max(0, intent),
        "context": max(0, context),
        "constraints": max(0, constraints),
        "output": max(0, output),
        "robustness": max(0, robustness),
        "security": max(0, security),
    }


def _compute_score(categories: dict[str, int]) -> int:
    total = sum(categories.values())
    # Scale to 100 (max raw = 110)
    return min(100, round(total * 100 / 110))
