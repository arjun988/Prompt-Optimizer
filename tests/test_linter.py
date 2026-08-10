from openprompt.core.linter.linter import Severity, lint
from openprompt.core.parser.parser import parse_text


def test_lint_detects_ambiguity() -> None:
    ast = parse_text("Make it good.")
    report = lint(ast)
    assert any(i.code == "ambiguous_objective" for i in report.issues)
    assert report.score < 100


def test_lint_detects_contradiction() -> None:
    ast = parse_text("Be concise.\nProvide a comprehensive explanation covering every detail.")
    report = lint(ast)
    assert any(i.code == "conflicting_instructions" for i in report.issues)


def test_lint_structured_prompt_scores_higher() -> None:
    ast = parse_text(
        "You are a senior engineer.\n\n"
        "Summarize the article.\n\n"
        "Constraints:\n- Be accurate\n\n"
        "Output:\n- markdown sections"
    )
    report = lint(ast)
    assert report.score >= 50
