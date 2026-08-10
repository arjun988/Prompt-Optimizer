"""Add or refine role/persona based on task type."""

from __future__ import annotations

from openprompt.core.ast.models import ObjectiveSpec, PromptAST, RoleSpec
from openprompt.strategies.mutations.base import OptimizeContext

ROLE_BY_TASK = {
    "code_review": "a senior software engineer performing a thorough code review",
    "debugging": "an expert debugger specializing in root-cause analysis",
    "summarization": "a technical writer who produces concise, accurate summaries",
    "classification": "a precise classifier that follows label definitions strictly",
    "extraction": "a data extraction specialist focused on faithful structured output",
    "explanation": "a senior engineer who explains complex topics clearly",
    "analysis": "an analytical expert who cites evidence from provided material only",
}


class RoleMutation:
    name = "role"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        task = updated.objective.task if updated.objective else None

        if updated.role and updated.role.enabled and updated.role.description:
            return updated

        description = ROLE_BY_TASK.get(task or "", "an expert assistant")
        updated.role = RoleSpec(description=description, enabled=True)

        if not updated.objective:
            updated.objective = ObjectiveSpec(task=task, raw=ast.raw_text or "Complete the task.")

        return updated
