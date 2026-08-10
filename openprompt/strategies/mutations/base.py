"""Mutation operator framework for prompt optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from openprompt.core.ast.models import PromptAST
from openprompt.core.linter.linter import LintReport


@dataclass
class OptimizeContext:
    lint_report: LintReport | None = None
    failures: list[str] = field(default_factory=list)
    task_embedding: list[float] = field(default_factory=list)
    eval_budget_remaining: int = 100
    prefer_compression: bool = False


class MutationOperator(Protocol):
    name: str

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST: ...


def builtin_operators() -> list[MutationOperator]:
    from openprompt.strategies.mutations.compression import CompressionMutation
    from openprompt.strategies.mutations.constraint import ConstraintMutation
    from openprompt.strategies.mutations.context import ContextMutation
    from openprompt.strategies.mutations.example import ExampleMutation
    from openprompt.strategies.mutations.output import OutputMutation
    from openprompt.strategies.mutations.reasoning import ReasoningMutation
    from openprompt.strategies.mutations.role import RoleMutation
    from openprompt.strategies.mutations.security import SecurityMutation
    from openprompt.strategies.mutations.structure import StructureMutation

    return [
        RoleMutation(),
        ConstraintMutation(),
        ContextMutation(),
        OutputMutation(),
        ExampleMutation(),
        StructureMutation(),
        CompressionMutation(),
        SecurityMutation(),
        ReasoningMutation(),
    ]


def default_operators() -> list[MutationOperator]:
    """Built-in operators plus entry-point plugins."""
    from openprompt.plugins.discovery import discover_mutation_operators

    return discover_mutation_operators()


OPERATOR_BY_NAME: dict[str, str] = {
    "role": "RoleMutation",
    "constraint": "ConstraintMutation",
    "context": "ContextMutation",
    "output": "OutputMutation",
    "example": "ExampleMutation",
    "structure": "StructureMutation",
    "compression": "CompressionMutation",
    "security": "SecurityMutation",
    "reasoning": "ReasoningMutation",
    "clarity": "ClarityMutation",
}
