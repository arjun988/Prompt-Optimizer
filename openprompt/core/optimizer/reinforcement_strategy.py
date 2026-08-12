"""Low-call reinforcement optimization — batch eval + test-driven rewrites."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.core.evaluator.metrics import TestCase, run_batch_evaluation
from openprompt.core.linter.linter import lint
from openprompt.core.optimizer.failure_analysis import analyze_failures
from openprompt.core.optimizer.models import CandidateResult, OptimizeResult
from openprompt.core.optimizer.strategies import (
    EvalMetrics,
    StrategyContext,
    _build_critique,
    _heuristic_warnings,
    _objective_score,
    _provider_name,
    _model_name,
    _strategy_rewrite,
    _to_candidate,
)
from openprompt.core.parser.parser import parse_text
from openprompt.providers.base import Message, ModelProvider


def strategy_reinforcement(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """
    Test-driven reinforcement loop with batched evaluation (~5–6 API calls):

      1. Batch-eval baseline prompt against full CSV/YAML test suite (1 call)
      2. Rewrite prompt with test inputs + expected outputs + failure feedback (1 call)
      3. Batch-eval improved prompt (1 call)
      4. Repeat steps 2–3 until all tests pass or max rounds reached
    """
    config = ctx.config.optimizer if ctx.config else None
    max_rounds = config.reinforcement_rounds if config else 2

    if not ctx.tests:
        return _strategy_rewrite(ast, ctx)

    lint_report = lint(ast)
    objectives = ctx.config.objectives if ctx.config else None
    from openprompt.config.models import ObjectivesConfig

    objectives = objectives or ObjectivesConfig()
    eval_cfg = ctx.config.evaluation if ctx.config else None
    provider_name = _provider_name(ctx)
    model_name = _model_name(ctx)
    pass_threshold = eval_cfg.pass_threshold if eval_cfg else 0.85
    holdout_ratio = eval_cfg.holdout_ratio if eval_cfg else 0.0
    min_test_count = eval_cfg.min_test_count if eval_cfg else 3

    api_calls = 0
    candidates: list[CandidateResult] = []

    def _batch_metrics(candidate_ast: PromptAST) -> EvalMetrics:
        nonlocal api_calls
        from openprompt.plugins.discovery import discover_evaluators

        eval_report = run_batch_evaluation(
            candidate_ast,
            ctx.tests,  # type: ignore[arg-type]
            ctx.provider,
            judge_provider=ctx.judge_provider,
            custom_eval_fn=ctx.custom_eval_fn,
            plugin_evaluators=discover_evaluators(),
            provider_name=provider_name,
            model_name=model_name,
            pass_threshold=pass_threshold,
            holdout_ratio=holdout_ratio,
            min_test_count=min_test_count,
        )
        api_calls += 1
        cost = eval_report.total_cost_usd
        composite = _objective_score(eval_report.accuracy, candidate_ast.estimate_tokens(), cost, objectives)
        return EvalMetrics(
            composite_score=composite,
            quality_score=eval_report.accuracy,
            tokens=candidate_ast.estimate_tokens(),
            cost_usd=cost,
            latency_ms=eval_report.total_latency_ms,
            eval_report=eval_report,
        )

    original_metrics = _batch_metrics(ast.clone())
    candidates.append(_to_candidate(ast.clone(), original_metrics, "reinforcement", ["baseline"]))

    current = ast.clone()
    best = current
    best_metrics = original_metrics

    for round_index in range(max_rounds):
        if best_metrics.eval_report and not analyze_failures(best_metrics.eval_report.results):
            break

        failure_feedback = _format_eval_feedback(best_metrics.eval_report)
        test_context = _build_test_suite_context(ctx.tests)
        critique = _build_critique(lint_report)

        current = _reinforcement_rewrite(
            current,
            ctx.provider,
            critique=critique,
            test_context=test_context,
            failure_feedback=failure_feedback,
            round_index=round_index + 1,
        )
        api_calls += 1

        metrics = _batch_metrics(current)
        candidates.append(_to_candidate(current, metrics, "reinforcement", [f"rewrite_{round_index + 1}"]))

        if metrics.composite_score >= best_metrics.composite_score:
            best = current
            best_metrics = metrics

        if metrics.eval_report and not analyze_failures(metrics.eval_report.results):
            break

    failure_analyses = []
    if best_metrics.eval_report:
        failure_analyses = analyze_failures(best_metrics.eval_report.results)

    return OptimizeResult(
        original=ast,
        optimized=best,
        original_score=original_metrics.quality_score,
        optimized_score=best_metrics.quality_score,
        original_tokens=original_metrics.tokens,
        optimized_tokens=best_metrics.tokens,
        original_cost_usd=original_metrics.cost_usd,
        optimized_cost_usd=best_metrics.cost_usd,
        strategy="reinforcement",
        lint_report=lint_report,
        candidates=candidates,
        failure_analyses=failure_analyses,
        report_lines=[
            "Reinforcement optimization (batch eval + test-driven rewrites).",
            f"API calls used: {api_calls} (target ~5–6 for typical suites).",
            f"Rounds completed: {min(max_rounds, len(candidates))}",
        ],
        warnings=_heuristic_warnings(ctx),
    )


def _build_test_suite_context(tests: list[TestCase]) -> str:
    lines = ["Full test suite — optimize the prompt to pass every case:"]
    for test in tests:
        lines.append(f"\n- {test.name} [{test.metric.value}]")
        lines.append(f"  Input: {test.input.strip()}")
        if test.expected:
            lines.append(f"  Expected: {test.expected}")
        if test.pattern:
            lines.append(f"  Pattern: {test.pattern}")
    return "\n".join(lines)


def _format_eval_feedback(eval_report) -> str:
    if not eval_report or not eval_report.results:
        return ""

    lines = ["Latest evaluation results:"]
    for result in eval_report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"\n- {result.test.name}: {status} (score={result.score:.2f})")
        lines.append(f"  Model output: {result.output[:300]}")
        if not result.passed:
            lines.append(f"  Issue: {result.message}")
            if result.test.expected:
                lines.append(f"  Expected: {result.test.expected}")
            if result.test.pattern:
                lines.append(f"  Pattern: {result.test.pattern}")
    return "\n".join(lines)


def _reinforcement_rewrite(
    ast: PromptAST,
    provider: ModelProvider,
    *,
    critique: str,
    test_context: str,
    failure_feedback: str,
    round_index: int,
) -> PromptAST:
    original = render_generic(ast)
    messages = [
        Message(
            role="user",
            content=(
                "You are a prompt optimization expert. Improve the prompt so it passes ALL test cases.\n\n"
                f"{critique}\n\n"
                f"{test_context}\n\n"
                f"{failure_feedback}\n\n"
                f"Original prompt:\n{original}\n\n"
                f"Round {round_index}: apply targeted fixes for failing tests. "
                "Add explicit output format rules, constraints, and examples derived from the test suite. "
                "Return ONLY the improved prompt text. Do not wrap in markdown fences."
            ),
        )
    ]
    response = provider.generate(messages, temperature=0.4)
    improved = parse_text(response.content.strip())
    improved.metadata = ast.metadata.model_copy()
    return improved
