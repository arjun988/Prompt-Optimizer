from openprompt.core.compiler.renderer import render_generic, render_messages
from openprompt.core.ast.models import PromptAST


def test_render_generic(sample_ast: PromptAST) -> None:
    text = render_generic(sample_ast)
    assert "expert assistant" in text
    assert "Key points" in text


def test_render_messages_openai(sample_ast: PromptAST) -> None:
    messages = render_messages(sample_ast, provider="openai")
    assert messages[0].role == "system"


def test_render_messages_gemini(sample_ast: PromptAST) -> None:
    messages = render_messages(sample_ast, provider="gemini")
    assert len(messages) >= 1
