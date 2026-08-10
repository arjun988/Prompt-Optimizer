from openprompt.plugins.discovery import discover_mutation_operators
from openprompt.strategies.mutations.base import builtin_operators


def test_builtin_operators_count() -> None:
    assert len(builtin_operators()) >= 8


def test_plugin_operator_loaded() -> None:
    ops = discover_mutation_operators()
    names = {op.name for op in ops}
    assert "clarity" in names
    assert "role" in names


def test_plugin_operator_mutate_is_instance() -> None:
    from openprompt.core.ast.models import PromptAST
    from openprompt.strategies.mutations.base import OptimizeContext

    clarity = next(op for op in discover_mutation_operators() if op.name == "clarity")
    ast = PromptAST(raw_text="Summarize this.")
    result = clarity.mutate(ast, OptimizeContext())
    assert "clear, direct language" in " ".join(result.constraints).lower()
