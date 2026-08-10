"""Optimization result models."""

from __future__ import annotations

from dataclasses import dataclass, field

from openprompt.core.ast.models import PromptAST
from openprompt.core.linter.linter import LintReport
from openprompt.core.optimizer.failure_analysis import FailureAnalysis


@dataclass
class CandidateResult:
    ast: PromptAST
    score: float
    lint_score: int
    tokens: int
    strategy: str
    quality_score: float = 0.0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    operators_applied: list[str] = field(default_factory=list)


@dataclass
class OptimizeResult:
    original: PromptAST
    optimized: PromptAST
    original_score: float
    optimized_score: float
    original_tokens: int
    optimized_tokens: int
    strategy: str
    lint_report: LintReport | None = None
    candidates: list[CandidateResult] = field(default_factory=list)
    failure_analyses: list[FailureAnalysis] = field(default_factory=list)
    report_lines: list[str] = field(default_factory=list)
    original_cost_usd: float = 0.0
    optimized_cost_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)

    @property
    def cost_delta_pct(self) -> float:
        if self.original_cost_usd == 0:
            return 0.0
        return (self.optimized_cost_usd - self.original_cost_usd) / self.original_cost_usd * 100

    @property
    def score_delta(self) -> float:
        return self.optimized_score - self.original_score

    @property
    def token_delta_pct(self) -> float:
        if self.original_tokens == 0:
            return 0.0
        return (self.optimized_tokens - self.original_tokens) / self.original_tokens * 100

    @property
    def prompt(self) -> str:
        from openprompt.core.compiler.renderer import render_generic

        return render_generic(self.optimized)
