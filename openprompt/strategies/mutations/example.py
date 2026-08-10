"""Normalize and enhance few-shot examples."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.strategies.mutations.base import OptimizeContext


class ExampleMutation:
    name = "example"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        # Without user examples, this operator is a no-op.
        # When examples exist, ensure consistent formatting labels.
        updated = ast.clone()
        if not updated.examples:
            return updated

        for index, example in enumerate(updated.examples):
            if not example.label:
                updated.examples[index] = example.model_copy(
                    update={"label": f"Example {index + 1}"}
                )
        return updated
