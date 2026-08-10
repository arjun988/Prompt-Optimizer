"""Optimization strategies: rewrite, iterative, evolutionary, hybrid, compress."""

from __future__ import annotations

from dataclasses import dataclass

from openprompt.config.models import ObjectivesConfig, ProjectConfig
from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.core.cost.pricing import estimate_tokens_cost_usd
from openprompt.core.evaluator.metrics import EvalReport, TestCase, run_evaluation
from openprompt.core.linter.linter import lint
from openprompt.core.optimizer.bandit import LinUCBBandit, build_context_features
from openprompt.core.optimizer.crossover import crossover_ast
from openprompt.core.optimizer.failure_analysis import analyze_failures
from openprompt.core.optimizer.models import CandidateResult, OptimizeResult
from openprompt.core.optimizer.pareto import ObjectiveVector, RankedIndividual, nsga2_select, to_ranked
from openprompt.core.security.scanner import scan
from openprompt.providers.base import Message, ModelProvider
from openprompt.strategies.mutations.base import MutationOperator, OptimizeContext, default_operators


@dataclass
class StrategyContext:
    provider: ModelProvider
    judge_provider: ModelProvider | None = None
    tests: list[TestCase] | None = None
    config: ProjectConfig | None = None
    custom_eval_fn=None


@dataclass
class EvalMetrics:
    composite_score: float
    quality_score: float
    tokens: int
    cost_usd: float
    latency_ms: float
    eval_report: EvalReport | None = None


def run_strategy(ast: PromptAST, strategy: str, ctx: StrategyContext) -> OptimizeResult:
    runners = {
        "rewrite": _strategy_rewrite,
        "iterative": _strategy_iterative,
        "evolutionary": _strategy_evolutionary,
        "hybrid": _strategy_hybrid,
        "compress": _strategy_compress,
    }
    return runners.get(strategy, _strategy_hybrid)(ast, ctx)


def _provider_name(ctx: StrategyContext) -> str:
    if ctx.config:
        return ctx.config.model.provider
    return getattr(ctx.provider, "name", "mock")


def _model_name(ctx: StrategyContext) -> str:
    if ctx.config:
        return ctx.config.model.name
    return getattr(ctx.provider, "model", "mock-model")


def _objective_score(
    quality: float,
    tokens: int,
    cost: float,
    objectives: ObjectivesConfig,
) -> float:
    token_penalty = min(1.0, tokens / 4000.0)
    return (
        objectives.quality_weight * quality
        - objectives.token_weight * token_penalty
        - objectives.cost_weight * min(1.0, cost * 100.0)
    )


def _evaluate_ast(ast: PromptAST, ctx: StrategyContext) -> EvalMetrics:
    objectives = ctx.config.objectives if ctx.config else ObjectivesConfig()
    provider_name = _provider_name(ctx)
    model_name = _model_name(ctx)
    tokens = ast.estimate_tokens()

    if not ctx.tests:
        lint_report = lint(ast)
        security = scan(ast)
        quality = (lint_report.score + security.score) / 200.0
        cost = estimate_tokens_cost_usd(tokens, tokens // 4, provider=provider_name, model=model_name)
        composite = _objective_score(quality, tokens, cost, objectives)
        return EvalMetrics(composite, quality, tokens, cost, 0.0, None)

    eval_report = run_evaluation(
        ast,
        ctx.tests,
        ctx.provider,
        judge_provider=ctx.judge_provider,
        custom_eval_fn=ctx.custom_eval_fn,
        provider_name=provider_name,
        model_name=model_name,
    )
    cost = eval_report.total_cost_usd or estimate_tokens_cost_usd(
        tokens, sum(len(r.output) // 4 for r in eval_report.results),
        provider=provider_name,
        model=model_name,
    )
    composite = _objective_score(eval_report.accuracy, tokens, cost, objectives)
    return EvalMetrics(
        composite_score=composite,
        quality_score=eval_report.accuracy,
        tokens=tokens,
        cost_usd=cost,
        latency_ms=eval_report.total_latency_ms,
        eval_report=eval_report,
    )


def _to_candidate(ast: PromptAST, metrics: EvalMetrics, strategy: str, ops: list[str] | None = None) -> CandidateResult:
    return CandidateResult(
        ast=ast,
        score=metrics.composite_score,
        lint_score=lint(ast).score,
        tokens=metrics.tokens,
        strategy=strategy,
        quality_score=metrics.quality_score,
        cost_usd=metrics.cost_usd,
        latency_ms=metrics.latency_ms,
        operators_applied=ops or [],
    )


def _objective_vector(candidate: CandidateResult) -> ObjectiveVector:
    return ObjectiveVector(
        quality=candidate.quality_score,
        tokens=candidate.tokens,
        cost_usd=candidate.cost_usd,
    )


def _nsga_select(pool: list[CandidateResult], k: int) -> list[CandidateResult]:
    if len(pool) <= k:
        return pool
    ranked = to_ranked(pool, _objective_vector)
    selected = nsga2_select(ranked, k)
    return selected


def _strategy_rewrite(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    lint_report = lint(ast)
    orig = _evaluate_ast(ast, ctx)
    optimized_ast = _llm_rewrite(ast, ctx.provider, _build_critique(lint_report))
    opt = _evaluate_ast(optimized_ast, ctx)
    failures = analyze_failures(opt.eval_report.results) if opt.eval_report else []

    return OptimizeResult(
        original=ast,
        optimized=optimized_ast,
        original_score=orig.quality_score,
        optimized_score=opt.quality_score,
        original_tokens=orig.tokens,
        optimized_tokens=opt.tokens,
        original_cost_usd=orig.cost_usd,
        optimized_cost_usd=opt.cost_usd,
        strategy="rewrite",
        lint_report=lint_report,
        failure_analyses=failures,
        report_lines=["Single-pass linter-guided rewrite.", f"Linter score: {lint_report.score}/100"],
    )


def _strategy_iterative(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    config = ctx.config.optimizer if ctx.config else None
    max_iterations = config.max_iterations if config else 3

    current = ast.clone()
    best = current
    best_metrics = _evaluate_ast(current, ctx)
    original_metrics = best_metrics
    candidates: list[CandidateResult] = []
    history: list[str] = []

    for iteration in range(max_iterations):
        critique = _build_critique(lint(current))
        if history:
            critique += "\n\nPrevious attempts:\n" + "\n".join(history[-5:])

        candidate_ast = _llm_rewrite(current, ctx.provider, critique)
        metrics = _evaluate_ast(candidate_ast, ctx)
        candidates.append(_to_candidate(candidate_ast, metrics, "iterative"))
        history.append(f"Iteration {iteration + 1}: quality={metrics.quality_score:.3f}")

        if metrics.composite_score > best_metrics.composite_score:
            best_metrics = metrics
            best = candidate_ast
        current = candidate_ast

        if metrics.eval_report and not analyze_failures(metrics.eval_report.results):
            break

    return OptimizeResult(
        original=ast,
        optimized=best,
        original_score=original_metrics.quality_score,
        optimized_score=best_metrics.quality_score,
        original_tokens=original_metrics.tokens,
        optimized_tokens=best_metrics.tokens,
        original_cost_usd=original_metrics.cost_usd,
        optimized_cost_usd=best_metrics.cost_usd,
        strategy="iterative",
        candidates=candidates,
        report_lines=[f"OPRO-style iterative optimization ({max_iterations} max iterations)."],
    )


def _strategy_evolutionary(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    config = ctx.config.optimizer if ctx.config else None
    population_size = config.candidates_per_gen if config else 8
    generations = config.max_iterations if config else 5
    budget = config.eval_budget if config else 50

    operators = default_operators()
    pool: list[CandidateResult] = []

    base_metrics = _evaluate_ast(ast, ctx)
    pool.append(_to_candidate(ast.clone(), base_metrics, "evolutionary"))
    eval_calls = 1

    for _gen in range(generations):
        if eval_calls >= budget:
            break

        parents = _nsga_select(pool, k=max(2, population_size // 2))

        # Crossover between top Pareto parents
        if len(parents) >= 2 and eval_calls < budget:
            child_ast = crossover_ast(parents[0].ast, parents[1].ast)
            metrics = _evaluate_ast(child_ast, ctx)
            eval_calls += 1
            pool.append(_to_candidate(child_ast, metrics, "evolutionary", ["crossover"]))

        for parent in parents:
            if eval_calls >= budget:
                break
            for op in operators:
                if eval_calls >= budget:
                    break
                child_ast = op.mutate(parent.ast, OptimizeContext(lint_report=lint(parent.ast)))
                metrics = _evaluate_ast(child_ast, ctx)
                eval_calls += 1
                pool.append(_to_candidate(child_ast, metrics, "evolutionary", [op.name]))

        pool = _nsga_select(pool, k=population_size)

    best = max(pool, key=lambda c: (c.quality_score, -c.tokens, -c.cost_usd))
    return OptimizeResult(
        original=ast,
        optimized=best.ast,
        original_score=base_metrics.quality_score,
        optimized_score=best.quality_score,
        original_tokens=base_metrics.tokens,
        optimized_tokens=best.tokens,
        original_cost_usd=base_metrics.cost_usd,
        optimized_cost_usd=best.cost_usd,
        strategy="evolutionary",
        candidates=pool,
        report_lines=[f"Evolutionary NSGA-II search with crossover ({eval_calls} evaluations)."],
    )


def _strategy_hybrid(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """
    Full HEDO loop per PRD §6.4:
      1. Parse & diagnose (done upstream)
      2. OPRO-style seed generation (~20% budget)
      3. Evolutionary loop with bandit operator selection
      4. Failure-driven refinement (TextGrad-style)
      5. Pareto winner selection
    """
    config = ctx.config.optimizer if ctx.config else None
    budget = config.eval_budget if config else 50
    population_size = config.candidates_per_gen if config else 8
    seed_count = max(3, budget // 5)

    operators = default_operators()
    bandit = LinUCBBandit(operators=operators)
    lint_report = lint(ast)
    original_metrics = _evaluate_ast(ast, ctx)

    pool: list[CandidateResult] = [
        _to_candidate(ast.clone(), original_metrics, "hybrid", ["baseline"])
    ]
    eval_calls = 1
    failures: list[str] = []
    if original_metrics.eval_report:
        failures = [f.category for f in analyze_failures(original_metrics.eval_report.results)]

    # Layer 1 — OPRO seeds (~20% budget)
    critique = _build_critique(lint_report)
    for i in range(min(seed_count, budget - eval_calls)):
        seed_ast = _llm_rewrite(
            ast,
            ctx.provider,
            f"{critique}\nVariant {i + 1}: apply distinct, measurable improvements.",
        )
        metrics = _evaluate_ast(seed_ast, ctx)
        eval_calls += 1
        pool.append(_to_candidate(seed_ast, metrics, "hybrid", ["llm_seed"]))
        if metrics.eval_report:
            failures = [f.category for f in analyze_failures(metrics.eval_report.results)]

    # Layer 2 — Evolutionary + bandit (remaining budget)
    while eval_calls < budget:
        parents = _nsga_select(pool, k=min(2, len(pool)))
        if len(parents) >= 2 and eval_calls < budget:
            crossed = crossover_ast(parents[0].ast, parents[1].ast)
            metrics = _evaluate_ast(crossed, ctx)
            eval_calls += 1
            pool.append(_to_candidate(crossed, metrics, "hybrid", ["crossover"]))

        parent = parents[0]
        features = build_context_features(parent.lint_score, failures, parent.tokens)
        op = bandit.select(features)
        child_ast = op.mutate(parent.ast, OptimizeContext(lint_report=lint(parent.ast), failures=failures))
        metrics = _evaluate_ast(child_ast, ctx)
        eval_calls += 1
        bandit.update(op.name, features, metrics.composite_score - parent.score)
        pool.append(_to_candidate(child_ast, metrics, "hybrid", [op.name]))

        if metrics.eval_report:
            failures = [f.category for f in analyze_failures(metrics.eval_report.results)]

        pool = _nsga_select(pool, k=population_size)

    # Layer 3 — Failure-driven patches
    best_so_far = max(pool, key=lambda c: (c.quality_score, -c.tokens))
    if ctx.tests and eval_calls < budget:
        eval_report = run_evaluation(
            best_so_far.ast,
            ctx.tests,
            ctx.provider,
            judge_provider=ctx.judge_provider,
            provider_name=_provider_name(ctx),
            model_name=_model_name(ctx),
        )
        op_map = {op.name: op for op in operators}
        patched = best_so_far.ast.clone()
        for fa in analyze_failures(eval_report.results)[:3]:
            op = op_map.get(fa.recommended_operator)
            if op:
                patched = op.mutate(patched, OptimizeContext(failures=[fa.category]))
        metrics = _evaluate_ast(patched, ctx)
        eval_calls += 1
        if metrics.quality_score >= best_so_far.quality_score:
            pool.append(_to_candidate(patched, metrics, "hybrid", ["failure_patch"]))

    best = max(pool, key=lambda c: (c.quality_score, -c.tokens, -c.cost_usd))
    failure_analyses = []
    if ctx.tests:
        final_eval = run_evaluation(
            best.ast,
            ctx.tests,
            ctx.provider,
            judge_provider=ctx.judge_provider,
            provider_name=_provider_name(ctx),
            model_name=_model_name(ctx),
        )
        failure_analyses = analyze_failures(final_eval.results)

    return OptimizeResult(
        original=ast,
        optimized=best.ast,
        original_score=original_metrics.quality_score,
        optimized_score=best.quality_score,
        original_tokens=original_metrics.tokens,
        optimized_tokens=best.tokens,
        original_cost_usd=original_metrics.cost_usd,
        optimized_cost_usd=best.cost_usd,
        strategy="hybrid",
        lint_report=lint_report,
        candidates=pool,
        failure_analyses=failure_analyses,
        report_lines=[
            "Hybrid eval-driven optimization (OPRO + NSGA-II + bandit + crossover + failure patches).",
            f"Evaluations used: {eval_calls}/{budget}",
        ],
    )


def _strategy_compress(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    from openprompt.strategies.mutations.compression import CompressionMutation

    original = _evaluate_ast(ast, ctx)
    current = ast.clone()
    best = current
    best_metrics = original

    for _ in range(5):
        current = CompressionMutation().mutate(current, OptimizeContext(prefer_compression=True))
        metrics = _evaluate_ast(current, ctx)
        if metrics.quality_score >= original.quality_score * 0.98:
            best = current
            best_metrics = metrics

    return OptimizeResult(
        original=ast,
        optimized=best,
        original_score=original.quality_score,
        optimized_score=best_metrics.quality_score,
        original_tokens=original.tokens,
        optimized_tokens=best_metrics.tokens,
        original_cost_usd=original.cost_usd,
        optimized_cost_usd=best_metrics.cost_usd,
        strategy="compress",
        report_lines=["Token compression while preserving ≥98% quality."],
    )


def _build_critique(lint_report) -> str:
    lines = ["Prompt issues to fix:"]
    for issue in lint_report.issues:
        if issue.severity.value in {"error", "warning"}:
            lines.append(f"- [{issue.code}] {issue.message}")
            if issue.recommendation:
                lines.append(f"  Recommendation: {issue.recommendation}")
    return "\n".join(lines)


def _llm_rewrite(ast: PromptAST, provider: ModelProvider, critique: str) -> PromptAST:
    from openprompt.core.parser.parser import parse_text

    original = render_generic(ast)
    messages = [
        Message(
            role="user",
            content=(
                "You are a prompt optimization expert. Improve the following prompt.\n\n"
                f"{critique}\n\n"
                f"Original prompt:\n{original}\n\n"
                "Return ONLY the improved prompt text. Preserve intent. Add structure, "
                "constraints, and output format where missing. Do not wrap in markdown fences."
            ),
        )
    ]
    response = provider.generate(messages, temperature=0.5)
    improved = parse_text(response.content.strip())
    improved.metadata = ast.metadata.model_copy()
    return improved
