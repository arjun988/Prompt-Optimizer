"""Token counting with tiktoken fallback."""

from __future__ import annotations

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic


def estimate_tokens(text: str, *, model: str | None = None) -> int:
    """Count tokens using tiktoken when available, else char heuristic."""
    if not text:
        return 1
    try:
        import tiktoken

        encoding_name = "cl100k_base"
        if model:
            try:
                encoding = tiktoken.encoding_for_model(model)
            except KeyError:
                encoding = tiktoken.get_encoding(encoding_name)
        else:
            encoding = tiktoken.get_encoding(encoding_name)
        return max(1, len(encoding.encode(text)))
    except ImportError:
        return max(1, len(text) // 4)


def estimate_tokens_from_ast(ast: PromptAST, *, model: str | None = None) -> int:
    return estimate_tokens(render_generic(ast), model=model)
