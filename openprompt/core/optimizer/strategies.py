"""Optimization strategies: rewrite, iterative, evolutionary, hybrid, compress."""

from __future__ import annotations

from dataclasses import dataclass

from openprompt.config.models import ObjectivesConfig, ProjectConfig
from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.core.compiler.tokens import estimate_tokens_from_ast
from openprompt.core.evaluator.metrics import EvalReport, TestCase, run_evaluation
from openprompt.core.linter.linter import lint
from openprompt.core.optimizer.bandit import LinUCBBandit, build_context_features
from openprompt.core.optimizer.failure_analysis import analyze_failures
from openprompt.core.optimizer.models import CandidateResult, OptimizeResult
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


def run_strategy(
    ast: PromptAST,
    strategy: str,
    ctx: StrategyContext,
) -> OptimizeResult:
    runners = {
        "rewrite": _strategy_rewrite,
        "iterative": _strategy_iterative,
        "evolutionary": _strategy_evolutionary,
        "hybrid": _strategy_hybrid,
        "compress": _strategy_compress,
    }
    runner = runners.get(strategy, _strategy_hybrid)
    return runner(ast, ctx)


def _objective_score(
    eval_score: float,
    tokens: int,
    cost: float,
    objectives: ObjectivesConfig,
) -> float:
    token_penalty = min(1.0, tokens / 4000.0)
    return (
        objectives.quality_weight * eval_score
        - objectives.token_weight * token_penalty
        - objectives.cost_weight * cost
    )


def _evaluate_ast(ast: PromptAST, ctx: StrategyContext) -> tuple[float, EvalReport | None]:
    if not ctx.tests:
        report = lint(ast)
        security = scan(ast)
        heuristic = (report.score + security.score) / 200.0
        return heuristic, None

    eval_report = run_evaluation(
        ast,
        ctx.tests,
        ctx.provider,
        judge_provider=ctx.judge_provider,
        custom_eval_fn=ctx.custom_eval_fn,
    )
    objectives = ctx.config.objectives if ctx.config else ObjectivesConfig()
    cost = 0.001  # placeholder small cost
    score = _objective_score(eval_report.accuracy, ast.estimate_tokens(), cost, objectives)
    return score, eval_report


def _strategy_rewrite(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    lint_report = lint(ast)
    original_score, _ = _evaluate_ast(ast, ctx)

    critique = _build_critique(lint_report)
    optimized_ast = _llm_rewrite(ast, ctx.provider, critique)
    optimized_score, eval_report = _evaluate_ast(optimized_ast, ctx)

    failures = analyze_failures(eval_report.results) if eval_report else []

    return OptimizeResult(
        original=ast,
        optimized=optimized_ast,
        original_score=original_score,
        optimized_score=optimized_score,
        original_tokens=ast.estimate_tokens(),
        optimized_tokens=optimized_ast.estimate_tokens(),
        strategy="rewrite",
        lint_report=lint_report,
        failure_analyses=failures,
        report_lines=[
            "Applied single-pass linter-guided rewrite.",
            f"Linter score: {lint_report.score}/100",
        ],
    )


def _strategy_iterative(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    config = ctx.config.optimizer if ctx.config else None
    max_iterations = config.max_iterations if config else 3

    current = ast.clone()
    best = current
    best_score, _ = _evaluate_ast(current, ctx)
    original_score = best_score
    candidates: list[CandidateResult] = []
    history: list[str] = []

    for iteration in range(max_iterations):
        lint_report = lint(current)
        critique = _build_critique(lint_report)
        if history:
            critique += "\n\nPrevious attempts and scores:\n" + "\n".join(history[-5:])

        candidate = _llm_rewrite(current, ctx.provider, critique)
        score, eval_report = _evaluate_ast(candidate, ctx)
        candidates.append(
            CandidateResult(
                ast=candidate,
                score=score,
                lint_score=lint_report.score,
                tokens=candidate.estimate_tokens(),
                strategy="iterative",
            )
        )
        history.append(f"Iteration {iteration + 1}: score={score:.3f}")

        if score > best_score:
            best_score = score
            best = candidate
        current = candidate

        if eval_report:
            failures = analyze_failures(eval_report.results)
            if not failures:
                break

    return OptimizeResult(
        original=ast,
        optimized=best,
        original_score=original_score,
        optimized_score=best_score,
        original_tokens=ast.estimate_tokens(),
        optimized_tokens=best.estimate_tokens(),
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

    base_score, _ = _evaluate_ast(ast, ctx)
    pool.append(
        CandidateResult(ast=ast.clone(), score=base_score, lint_score=lint(ast).score, tokens=ast.estimate_tokens(), strategy="evolutionary")
    )

    eval_calls = 1
    for _gen in range(generations):
        if eval_calls >= budget:
            break
        parents = _select_pareto(pool, k=max(2, population_size // 2))
        for parent in parents:
            if eval_calls >= budget:
                break
            for op in operators:
                if eval_calls >= budget:
                    break
                child_ast = op.mutate(parent.ast, OptimizeContext(lint_report=lint(parent.ast)))
                score, _ = _evaluate_ast(child_ast, ctx)
                eval_calls += 1
                pool.append(
                    CandidateResult(
                        ast=child_ast,
                        score=score,
                        lint_score=lint(child_ast).score,
                        tokens=child_ast.estimate_tokens(),
                        strategy="evolutionary",
                        operators_applied=[op.name],
                    )
                )

        pool = _elitism(pool, k=population_size)

    best = max(pool, key=lambda c: (c.score, -c.tokens))
    return OptimizeResult(
        original=ast,
        optimized=best.ast,
        original_score=base_score,
        optimized_score=best.score,
        original_tokens=ast.estimate_tokens(),
        optimized_tokens=best.tokens,
        strategy="evolutionary",
        candidates=pool,
        report_lines=[f"Evolutionary search: {eval_calls} evaluations."],
    )


def _strategy_hybrid(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    config = ctx.config.optimizer if ctx.config else None
    budget = config.eval_budget if config else 50
    seed_budget = max(3, budget // 5)

    operators = default_operators()
    bandit = LinUCBBandit(operators=operators)
    lint_report = lint(ast)
    original_score, orig_eval = _evaluate_ast(ast, ctx)

    pool: list[CandidateResult] = [
        CandidateResult(
            ast=ast.clone(),
            score=original_score,
            lint_score=lint_report.score,
            tokens=ast.estimate_tokens(),
            strategy="hybrid",
        )
    ]
    eval_calls = 1

    # Layer 1: OPRO-style seeds
    critique = _build_critique(lint_report)
    for i in range(min(3, seed_budget)):
        if eval_calls >= budget:
            break
        seed = _llm_rewrite(ast, ctx.provider, f"{critique}\nVariant {i + 1}: apply distinct improvements.")
        score, _ = _evaluate_ast(seed, ctx)
        eval_calls += 1
        pool.append(
            CandidateResult(
                ast=seed,
                score=score,
                lint_score=lint(seed).score,
                tokens=seed.estimate_tokens(),
                strategy="hybrid",
                operators_applied=["llm_seed"],
            )
        )

    # Layer 2: Evolutionary + bandit
    failures: list[str] = []
    if orig_eval:
        failures = [f.category for f in analyze_failures(orig_eval.results)]

    while eval_calls < budget:
        parents = _select_pareto(pool, k=2)
        parent = parents[0]
        features = build_context_features(parent.lint_score, failures, parent.tokens)
        op = bandit.select(features)
        child_ast = op.mutate(parent.ast, OptimizeContext(lint_report=lint(parent.ast), failures=failures))
        score, eval_report = _evaluate_ast(child_ast, ctx)
        eval_calls += 1
        reward = score - parent.score
        bandit.update(op.name, features, reward)
        pool.append(
            CandidateResult(
                ast=child_ast,
                score=score,
                lint_score=lint(child_ast).score,
                tokens=child_ast.estimate_tokens(),
                strategy="hybrid",
                operators_applied=[op.name],
            )
        )
        if eval_report:
            failures = [f.category for f in analyze_failures(eval_report.results)]

    # Layer 3: Failure-driven patches
    best_so_far = max(pool, key=lambda c: (c.score, -c.tokens))
    if ctx.tests and eval_calls < budget:
        eval_report = run_evaluation(
            best_so_far.ast, ctx.tests, ctx.provider, judge_provider=ctx.judge_provider
        )
        failure_analyses = analyze_failures(eval_report.results)
        patched = best_so_far.ast.clone()
        op_map = {op.name: op for op in operators}
        for fa in failure_analyses[:3]:
            op = op_map.get(fa.recommended_operator)
            if op:
                patched = op.mutate(patched, OptimizeContext(failures=[fa.category]))
        score, _ = _evaluate_ast(patched, ctx)
        if score >= best_so_far.score:
            pool.append(
                CandidateResult(
                    ast=patched,
                    score=score,
                    lint_score=lint(patched).score,
                    tokens=patched.estimate_tokens(),
                    strategy="hybrid",
                    operators_applied=["failure_patch"],
                )
            )

    best = max(pool, key=lambda c: (c.score, -c.tokens))
    failure_analyses = []
    if ctx.tests:
        final_eval = run_evaluation(
            best.ast, ctx.tests, ctx.provider, judge_provider=ctx.judge_provider
        )
        failure_analyses = analyze_failures(final_eval.results)

    return OptimizeResult(
        original=ast,
        optimized=best.ast,
        original_score=original_score,
        optimized_score=best.score,
        original_tokens=ast.estimate_tokens(),
        optimized_tokens=best.tokens,
        strategy="hybrid",
        lint_report=lint_report,
        candidates=pool,
        failure_analyses=failure_analyses,
        report_lines=[
            "Hybrid eval-driven optimization (OPRO seeds + evolutionary bandit + failure patches).",
            f"Evaluations used: {eval_calls}/{budget}",
        ],
    )


def _strategy_compress(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    from openprompt.strategies.mutations.compression import CompressionMutation

    original_score, _ = _evaluate_ast(ast, ctx)
    current = ast.clone()
    best = current
    best_score = original_score

    for _ in range(5):
        current = CompressionMutation().mutate(current, OptimizeContext(prefer_compression=True))
        score, _ = _evaluate_ast(current, ctx)
        if score >= best_score * 0.98:
            best = current
            best_score = score

    return OptimizeResult(
        original=ast,
        optimized=best,
        original_score=original_score,
        optimized_score=best_score,
        original_tokens=ast.estimate_tokens(),
        optimized_tokens=best.estimate_tokens(),
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


def _select_pareto(candidates: list[CandidateResult], k: int) -> list[CandidateResult]:
    """NSGA-II-inspired: prefer high score and low tokens."""
    ranked = sorted(candidates, key=lambda c: (-c.score, c.tokens))
    return ranked[:k]


def _elitism(candidates: list[CandidateResult], k: int) -> list[CandidateResult]:
    return _select_pareto(candidates, k)
