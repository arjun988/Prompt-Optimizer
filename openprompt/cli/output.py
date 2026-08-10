"""JSON-serializable CLI/API output helpers."""

from __future__ import annotations

import json
from typing import Any


def emit_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=_default)


def _default(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)
