"""GRPO-style meta-model mutation proposer — always eval-validated."""

from __future__ import annotations

import json
import re

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.core.optimizer.models import CandidateResult, OptimizeResult
from openprompt.core.optimizer.strategies import (
    StrategyContext,
    _evaluate_ast,
    _heuristic_warnings,
    _nsga_select,
    _provider_name,
    _to_candidate,
)
from openprompt.core.parser.parser import parse_text
from openprompt.providers.base import Message, ModelProvider


def strategy_grpo(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """
    Group Relative Policy Optimization (simplified):

    A cheap meta-model proposes structured prompt patches; each proposal is
    eval-validated before acceptance. Best candidates selected via Pareto.
    """
    config = ctx.config.optimizer if ctx.config else None
    meta_cfg = ctx.config.meta_model if ctx.config and ctx.config.meta_model else None
    budget = config.eval_budget if config else 30
    proposals_per_round = config.grpo_proposals if config else 4

    meta_provider = _meta_provider(ctx, meta_cfg)
    original_metrics = _evaluate_ast(ast, ctx)
    pool: list[CandidateResult] = [_to_candidate(ast.clone(), original_metrics, "grpo", ["baseline"])]
    eval_calls = 1
    report_lines = ["GRPO meta-model mutation search (eval-validated proposals)."]

    while eval_calls < budget:
        parent = _nsga_select([c for c in pool], k=1)[0] if pool else pool[0]
        for i in range(min(proposals_per_round, budget - eval_calls)):
            patch_ast = _propose_patch(parent.ast, meta_provider, ctx, variant=i + 1)
            metrics = _evaluate_ast(patch_ast, ctx)
            eval_calls += 1
            pool.append(_to_candidate(patch_ast, metrics, "grpo", ["meta_patch"]))
            if metrics.eval_report and all(r.passed for r in metrics.eval_report.results):
                report_lines.append(f"Proposal {i + 1}: all tests passed (quality={metrics.quality_score:.3f}).")
                break

    best = max(pool, key=lambda c: (c.quality_score, -c.tokens, -c.cost_usd))
    return OptimizeResult(
        original=ast,
        optimized=best.ast,
        original_score=original_metrics.quality_score,
        optimized_score=best.quality_score,
        original_tokens=original_metrics.tokens,
        optimized_tokens=best.tokens,
        original_cost_usd=original_metrics.cost_usd,
        optimized_cost_usd=best.cost_usd,
        strategy="grpo",
        candidates=pool,
        report_lines=report_lines + [f"Evaluations used: {eval_calls}/{budget}"],
        warnings=_heuristic_warnings(ctx),
    )


def _meta_provider(ctx: StrategyContext, meta_cfg) -> ModelProvider:
    from openprompt.providers.base import create_provider

    if meta_cfg:
        return create_provider(meta_cfg.provider, meta_cfg.model, warn_mock=False)
    return ctx.provider


def _propose_patch(
    ast: PromptAST,
    meta_provider: ModelProvider,
    ctx: StrategyContext,
    *,
    variant: int,
) -> PromptAST:
    current = render_generic(ast)
    failures = ""
    if ctx.tests:
        failures = f"\nFocus on test inputs like: {ctx.tests[0].input[:200]}"

    prompt = (
        "You are a prompt mutation proposer. Output a JSON object with optional keys: "
        "role, objective, constraints (list), context (list), output_format, examples (list of {input, output}). "
        "Only include fields that improve extraction accuracy. Variant {variant}.\n"
        f"Current prompt:\n{current}{failures}\n\n"
        'Return JSON only, e.g. {"constraints": ["Return valid JSON only"], "output_format": "json"}.'
    )
    response = meta_provider.generate([Message(role="user", content=prompt)], temperature=0.6)
    patch = _parse_patch_json(response.content)
    return _apply_patch(ast, patch)


def _parse_patch_json(content: str) -> dict:
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}


def _apply_patch(ast: PromptAST, patch: dict) -> PromptAST:
    from openprompt.core.ast.models import ExampleSpec, ObjectiveSpec, OutputFormat, OutputSpec, RoleSpec

    updated = ast.clone()
    if "role" in patch:
        updated.role = RoleSpec(description=str(patch["role"]), enabled=True)
    if "objective" in patch:
        updated.objective = ObjectiveSpec(raw=str(patch["objective"]))
    if "constraints" in patch and isinstance(patch["constraints"], list):
        updated.constraints = [str(c) for c in patch["constraints"]]
    if "context" in patch and isinstance(patch["context"], list):
        updated.context = [str(c) for c in patch["context"]]
    if patch.get("output_format") == "json":
        updated.output = OutputSpec(format=OutputFormat.JSON)
    if "examples" in patch and isinstance(patch["examples"], list):
        updated.examples = [
            ExampleSpec(input=str(e.get("input", "")), output=str(e.get("output", "")))
            for e in patch["examples"]
            if isinstance(e, dict)
        ]
    if patch.get("full_prompt"):
        return parse_text(str(patch["full_prompt"]))
    return updated
