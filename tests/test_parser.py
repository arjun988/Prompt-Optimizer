from pathlib import Path

from openprompt.core.parser.parser import parse_file, parse_text, parse_yaml


def test_parse_text_objective() -> None:
    ast = parse_text("Summarize this article in bullet points.")
    assert ast.objective
    assert ast.objective.task == "summarization"


def test_parse_yaml_structured() -> None:
    ast = parse_yaml(
        """
        prompt:
          role:
            description: senior engineer
          objective:
            task: code_review
        """
    )
    assert ast.role
    assert ast.role.description == "senior engineer"
    assert ast.objective
    assert ast.objective.task == "code_review"


def test_parse_examples_summarize_directory(examples_dir: Path) -> None:
    ast = parse_file(examples_dir / "summarize" / "prompt.txt")
    assert ast.objective
    assert "summarize" in (ast.objective.raw or "").lower()
