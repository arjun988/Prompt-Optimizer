"""Add standard constraints based on diagnosis."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.strategies.mutations.base import OptimizeContext

DEFAULT_CONSTRAINTS = [
    "Base answers only on provided information.",
    "Do not invent facts or issues unsupported by the input.",
    "If information is insufficient, state what is missing.",
]


class ConstraintMutation:
    name = "constraint"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        existing = {c.lower() for c in updated.constraints}

        for constraint in DEFAULT_CONSTRAINTS:
            if constraint.lower() not in existing:
                updated.constraints.append(constraint)

        if context.lint_report:
            for issue in context.lint_report.issues:
                if issue.code == "conflicting_instructions" and issue.recommendation:
                    rec = f"Resolve conflicts: {issue.recommendation}"
                    if rec.lower() not in existing:
                        updated.constraints.append(rec)

        return updated
