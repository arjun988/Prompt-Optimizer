"""Example custom evaluator for OpenPrompt projects."""

from __future__ import annotations


def evaluate(output: str, expected: str | None) -> float:
    """Score 1.0 if output contains expected text (case-insensitive)."""
    if expected is None:
        return 1.0 if output.strip() else 0.0
    return 1.0 if expected.lower() in output.lower() else 0.0
