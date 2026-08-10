"""Demo mutation operator registered via entry point."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.strategies.mutations.base import OptimizeContext


class ClarityMutation:
    """Plugin example: add clarity instruction to any prompt."""

    name = "clarity"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        marker = "Use clear, direct language."
        if marker.lower() not in {c.lower() for c in updated.constraints}:
            updated.constraints.append(marker)
        return updated
