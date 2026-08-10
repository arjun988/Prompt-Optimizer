"""Plugin discovery for mutation operators and evaluators."""

from __future__ import annotations

import importlib.metadata
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openprompt.strategies.mutations.base import MutationOperator

logger = logging.getLogger(__name__)

ENTRY_GROUP_OPERATORS = "openprompt.operators"
ENTRY_GROUP_EVALUATORS = "openprompt.evaluators"
ENTRY_GROUP_STRATEGIES = "openprompt.strategies"


def discover_mutation_operators() -> list[MutationOperator]:
    """Load built-in and entry-point registered mutation operators."""
    from openprompt.strategies.mutations.base import builtin_operators

    operators: list[MutationOperator] = builtin_operators()
    seen = {op.name for op in operators}

    try:
        eps = importlib.metadata.entry_points()
        group = eps.select(group=ENTRY_GROUP_OPERATORS) if hasattr(eps, "select") else eps.get(ENTRY_GROUP_OPERATORS, [])
    except Exception as exc:
        logger.debug("Plugin discovery failed: %s", exc)
        return operators

    for entry in group:
        try:
            loaded = entry.load()
            op = loaded() if callable(loaded) and not isinstance(loaded, type) else loaded
            if hasattr(op, "mutate") and hasattr(op, "name"):
                if op.name in seen:
                    logger.warning("Duplicate operator plugin ignored: %s", op.name)
                    continue
                operators.append(op)
                seen.add(op.name)
        except Exception as exc:
            logger.warning("Failed to load operator plugin %s: %s", entry.name, exc)

    return operators


def discover_evaluators() -> dict[str, object]:
    """Load entry-point registered custom evaluators."""
    discovered: dict[str, object] = {}
    try:
        eps = importlib.metadata.entry_points()
        group = eps.select(group=ENTRY_GROUP_EVALUATORS) if hasattr(eps, "select") else eps.get(ENTRY_GROUP_EVALUATORS, [])
    except Exception:
        return discovered

    for entry in group:
        try:
            discovered[entry.name] = entry.load()
        except Exception as exc:
            logger.warning("Failed to load evaluator plugin %s: %s", entry.name, exc)
    return discovered
