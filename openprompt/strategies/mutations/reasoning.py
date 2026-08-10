"""Add structured reasoning without exposing raw chain-of-thought."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST, ReasoningSpec
from openprompt.strategies.mutations.base import OptimizeContext

COMPLEX_TASKS = {"code_review", "debugging", "analysis", "extraction"}


class ReasoningMutation:
    name = "reasoning"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        task = updated.objective.task if updated.objective else None

        if task not in COMPLEX_TASKS and not context.failures:
            return updated

        updated.reasoning = ReasoningSpec(
            decompose=task in {"code_review", "analysis", "debugging"},
            verify=True,
            steps=[
                "Perform the analysis internally.",
                "Verify against requirements and constraints.",
                "Return only the final structured answer.",
            ],
        )
        return updated
