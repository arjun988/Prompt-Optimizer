from openprompt.core.ast.models import ObjectiveSpec, OutputSpec, PromptAST, RoleSpec
from openprompt.core.optimizer.crossover import crossover_ast


def test_crossover_merges_constraints() -> None:
    a = PromptAST(constraints=["A"], role=RoleSpec(description="engineer", enabled=True))
    b = PromptAST(
        constraints=["B"],
        output=OutputSpec(format="markdown", sections=["Summary"]),
        objective=ObjectiveSpec(task="code_review"),
    )
    child = crossover_ast(a, b)
    assert "A" in child.constraints and "B" in child.constraints
    assert child.output
    assert child.output.sections == ["Summary"]
