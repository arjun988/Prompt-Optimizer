"""Regression testing against a baseline."""

from __future__ import annotations

from dataclasses import dataclass

from openprompt.config.models import RegressionConfig
from openprompt.core.evaluator.metrics import EvalReport


@dataclass
class RegressionResult:
    passed: bool
    baseline_score: float
    current_score: float
    score_delta: float
    baseline_tokens: int
    current_tokens: int
    token_delta_pct: float
    messages: list[str]


def check_regression(
    baseline: EvalReport,
    current: EvalReport,
    config: RegressionConfig | None = None,
) -> RegressionResult:
    cfg = config or RegressionConfig()
    baseline_score = baseline.accuracy
    current_score = current.accuracy
    score_delta = current_score - baseline_score

    baseline_tokens = baseline.prompt_tokens
    current_tokens = current.prompt_tokens
    token_delta_pct = (
        (current_tokens - baseline_tokens) / baseline_tokens if baseline_tokens else 0.0
    )

    messages: list[str] = []
    passed = True

    if score_delta < cfg.min_score_delta:
        passed = False
        messages.append(
            f"Prompt regression detected: score dropped by {abs(score_delta):.1%} "
            f"({baseline_score:.1%} → {current_score:.1%})."
        )
    else:
        messages.append(f"Score OK: {baseline_score:.1%} → {current_score:.1%} ({score_delta:+.1%}).")

    if token_delta_pct > cfg.max_token_increase:
        passed = False
        messages.append(
            f"Token budget exceeded: +{token_delta_pct:.1%} "
            f"(max allowed: {cfg.max_token_increase:.1%})."
        )
    else:
        messages.append(f"Tokens OK: {baseline_tokens} → {current_tokens} ({token_delta_pct:+.1%}).")

    return RegressionResult(
        passed=passed,
        baseline_score=baseline_score,
        current_score=current_score,
        score_delta=score_delta,
        baseline_tokens=baseline_tokens,
        current_tokens=current_tokens,
        token_delta_pct=token_delta_pct,
        messages=messages,
    )
