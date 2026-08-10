"""Restructure prompt sections for clarity."""

from __future__ import annotations

from openprompt.core.ast.models import ObjectiveSpec, PromptAST, VerificationSpec
from openprompt.strategies.mutations.base import OptimizeContext


class StructureMutation:
    name = "structure"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()

        if updated.raw_text and not updated.objective:
            updated.objective = ObjectiveSpec(raw=updated.raw_text.strip())
            updated.raw_text = None

        if not updated.verification:
            updated.verification = VerificationSpec(
                enabled=True,
                steps=[
                    "Confirm all requirements are addressed.",
                    "Remove unsupported claims before responding.",
                ],
            )

        return updated
