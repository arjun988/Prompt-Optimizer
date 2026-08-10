from openprompt.plugins.discovery import discover_mutation_operators
from openprompt.strategies.mutations.base import builtin_operators


def test_builtin_operators_count() -> None:
    assert len(builtin_operators()) >= 8


def test_plugin_operator_loaded() -> None:
    ops = discover_mutation_operators()
    names = {op.name for op in ops}
    assert "clarity" in names
    assert "role" in names
