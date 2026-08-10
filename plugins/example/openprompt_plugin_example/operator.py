"""Example operator plugin package."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.strategies.mutations.base import OptimizeContext


class UppercaseConstraintMutation:
    """Example third-party operator: enforce uppercase section headers."""

    name = "uppercase_headers"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        marker = "Use uppercase section headers in the response."
        if marker not in updated.constraints:
            updated.constraints.append(marker)
        return updated
