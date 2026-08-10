"""RAG-focused mutation operator."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST, RAGSpec
from openprompt.strategies.mutations.base import OptimizeContext


class RAGMutation:
    name = "rag"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        rag = updated.rag or RAGSpec(enabled=True)
        rag.enabled = True
        rag.require_citations = True
        if rag.context_budget_tokens > 2500:
            rag.context_budget_tokens = max(1000, rag.context_budget_tokens - 400)
        updated.rag = rag
        if rag.retrieval_placeholder not in " ".join(updated.context):
            updated.context.append(
                f"Insert retrieved chunks at {rag.retrieval_placeholder}. "
                f"Cite as {rag.citation_format}."
            )
        return updated
