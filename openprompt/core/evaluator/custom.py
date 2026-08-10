"""Load custom Python evaluators from user files."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable


def load_custom_evaluator(path: Path | str) -> Callable[[str, str | None], float]:
    """
    Load an evaluator from a Python file.

    The file must define either:
      - evaluate(output, expected) -> float
      - Evaluator class with evaluate method
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Custom evaluator not found: {path}")

    spec = importlib.util.spec_from_file_location(f"openprompt_evaluator_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load evaluator module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if hasattr(module, "evaluate") and callable(module.evaluate):
        return module.evaluate

    if hasattr(module, "Evaluator"):
        instance = module.Evaluator()
        if hasattr(instance, "evaluate") and callable(instance.evaluate):
            return instance.evaluate

    raise ValueError(f"Evaluator file must define evaluate(output, expected): {path}")
