"""Add context placeholders for tasks that need them."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.strategies.mutations.base import OptimizeContext

CONTEXT_BY_TASK = {
    "code_review": ["Source code to review", "Language/runtime if known"],
    "debugging": ["Code snippet", "Expected behavior", "Observed behavior", "Error message", "Environment"],
    "extraction": ["Source document or text", "Fields to extract"],
    "analysis": ["Material to analyze", "Scope or focus areas"],
}


class ContextMutation:
    name = "context"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        task = updated.objective.task if updated.objective else None
        placeholders = CONTEXT_BY_TASK.get(task or "", [])

        existing = {c.lower() for c in updated.context}
        for placeholder in placeholders:
            entry = f"{placeholder}: {{...}}"
            if entry.lower() not in existing and placeholder.lower() not in existing:
                updated.context.append(entry)

        return updated
