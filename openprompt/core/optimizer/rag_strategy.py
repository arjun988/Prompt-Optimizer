"""RAG prompt optimization strategy."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST, RAGSpec
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.optimizer.strategies import (
    StrategyContext,
    _evaluate_ast,
    _heuristic_warnings,
    _strategy_hybrid,
)


def strategy_rag(ast: PromptAST, ctx: StrategyContext) -> OptimizeResult:
    """Optimize RAG-specific fields (context budget, citations) then run hybrid."""
    working = ast.clone()
    if not working.rag:
        working.rag = RAGSpec(enabled=True)

    config = ctx.config.optimizer if ctx.config else None
    budget_tokens = working.rag.context_budget_tokens

    # Tighten context budget if token pressure is high
    orig_metrics = _evaluate_ast(working, ctx)
    if orig_metrics.tokens > 3000 and working.rag.context_budget_tokens > 1500:
        working.rag.context_budget_tokens = max(800, budget_tokens - 500)

    if not working.rag.require_citations:
        working.rag.require_citations = True
        working.rag.citation_format = "[{index}]"

    if "{{retrieved_context}}" not in " ".join(working.context) and working.rag.retrieval_placeholder:
        working.context.append(
            f"Use retrieved context: {working.rag.retrieval_placeholder}. "
            f"Cite sources as {working.rag.citation_format}."
        )

    constraints = list(working.constraints)
    if working.rag.require_citations:
        constraints.append(
            f"Every factual claim must include a citation in format {working.rag.citation_format}."
        )
    if working.rag.context_budget_tokens:
        constraints.append(
            f"Stay within ~{working.rag.context_budget_tokens} tokens of retrieved context."
        )
    working.constraints = constraints

    result = _strategy_hybrid(working, ctx)
    result.strategy = "rag"
    result.report_lines = [
        "RAG optimization: context budget + citation rules + hybrid search.",
        *result.report_lines,
    ]
    result.warnings = _heuristic_warnings(ctx)
    return result
