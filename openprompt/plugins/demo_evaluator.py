"""Example evaluator plugin."""

from __future__ import annotations


def evaluate(output: str, expected: str | None) -> float:
    """Score 1.0 when output length is reasonable and contains expected text."""
    if not output.strip():
        return 0.0
    if expected and expected.lower() not in output.lower():
        return 0.0
    return 1.0 if len(output) >= 5 else 0.5
