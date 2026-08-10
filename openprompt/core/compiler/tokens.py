"""Token estimation utilities."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic


def estimate_tokens(text: str) -> int:
    """Rough token count (~4 characters per token)."""
    return max(1, len(text) // 4)


def estimate_tokens_from_ast(ast: PromptAST) -> int:
    return estimate_tokens(render_generic(ast))
