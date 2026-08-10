"""Plugin discovery for operators, evaluators, and strategies."""

from __future__ import annotations

import importlib.metadata
import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openprompt.core.ast.models import PromptAST
    from openprompt.core.optimizer.models import OptimizeResult
    from openprompt.core.optimizer.strategies import StrategyContext
    from openprompt.strategies.mutations.base import MutationOperator

logger = logging.getLogger(__name__)

ENTRY_GROUP_OPERATORS = "openprompt.operators"
ENTRY_GROUP_EVALUATORS = "openprompt.evaluators"
ENTRY_GROUP_STRATEGIES = "openprompt.strategies"

StrategyRunner = Callable[["PromptAST", "StrategyContext"], "OptimizeResult"]

_CACHE: dict[str, object] = {}


def clear_plugin_cache() -> None:
    _CACHE.clear()


def _entry_points(group: str):
    try:
        eps = importlib.metadata.entry_points()
        if hasattr(eps, "select"):
            return eps.select(group=group)
        return eps.get(group, [])
    except Exception as exc:
        logger.debug("Entry point load failed for %s: %s", group, exc)
        return []


def discover_mutation_operators() -> list[MutationOperator]:
    """Load built-in and entry-point registered mutation operators."""
    if "operators" not in _CACHE:
        _CACHE["operators"] = _load_mutation_operators()
    return _CACHE["operators"]  # type: ignore[return-value]


def _load_mutation_operators() -> list[MutationOperator]:
    from openprompt.strategies.mutations.base import builtin_operators

    operators: list[MutationOperator] = builtin_operators()
    seen = {op.name for op in operators}

    for entry in _entry_points(ENTRY_GROUP_OPERATORS):
        try:
            loaded = entry.load()
            op = _coerce_operator(loaded)
            if hasattr(op, "mutate") and hasattr(op, "name"):
                if op.name in seen:
                    logger.warning("Duplicate operator plugin ignored: %s", op.name)
                    continue
                operators.append(op)
                seen.add(op.name)
        except Exception as exc:
            logger.warning("Failed to load operator plugin %s: %s", entry.name, exc)

    return operators


def discover_evaluators() -> dict[str, Any]:
    """Load entry-point registered evaluators (callable or Evaluator class)."""
    if "evaluators" not in _CACHE:
        _CACHE["evaluators"] = _load_evaluators()
    return _CACHE["evaluators"]  # type: ignore[return-value]


def _load_evaluators() -> dict[str, Any]:
    discovered: dict[str, Any] = {}

    for entry in _entry_points(ENTRY_GROUP_EVALUATORS):
        try:
            loaded = entry.load()
            if callable(loaded):
                discovered[entry.name] = loaded
            elif hasattr(loaded, "evaluate"):
                discovered[entry.name] = loaded.evaluate
        except Exception as exc:
            logger.warning("Failed to load evaluator plugin %s: %s", entry.name, exc)

    return discovered


def discover_strategies() -> dict[str, StrategyRunner]:
    """
    Load built-in and plugin optimization strategies.

    Plugins register callables: ``(ast, ctx) -> OptimizeResult``
    or classes with a ``run(ast, ctx)`` method.
    """
    if "strategies" not in _CACHE:
        _CACHE["strategies"] = _load_strategies()
    return _CACHE["strategies"]  # type: ignore[return-value]


def _load_strategies() -> dict[str, StrategyRunner]:
    from openprompt.core.optimizer.strategies import builtin_strategy_runners

    strategies: dict[str, StrategyRunner] = dict(builtin_strategy_runners())

    for entry in _entry_points(ENTRY_GROUP_STRATEGIES):
        try:
            loaded = entry.load()
            if isinstance(loaded, type) and hasattr(loaded, "run"):
                instance = loaded()
                name = getattr(instance, "name", entry.name)
                strategies[name] = instance.run
            elif hasattr(loaded, "run") and callable(loaded.run):
                name = getattr(loaded, "name", entry.name)
                strategies[name] = loaded.run
            elif callable(loaded):
                strategies[entry.name] = loaded
        except Exception as exc:
            logger.warning("Failed to load strategy plugin %s: %s", entry.name, exc)

    return strategies


def _is_factory(obj: object) -> bool:
    return callable(obj) and not isinstance(obj, type) and not hasattr(obj, "run")


def _coerce_operator(loaded: object) -> object:
    """Instantiate operator classes; call factory functions."""
    if isinstance(loaded, type) and hasattr(loaded, "mutate"):
        return loaded()
    if _is_factory(loaded):
        return loaded()
    return loaded
