from pathlib import Path

from typer.testing import CliRunner

from openprompt.cli.main import app

runner = CliRunner()


def test_cli_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "optimize" in result.stdout


def test_cli_lint_offline(examples_dir: Path) -> None:
    path = examples_dir / "summarize" / "prompt.txt"
    result = runner.invoke(app, ["lint", str(path)])
    assert result.exit_code == 0
    assert "Prompt Analysis" in result.stdout


def test_cli_eval_directory(examples_dir: Path) -> None:
    result = runner.invoke(app, ["eval", str(examples_dir / "summarize")])
    assert result.exit_code == 0
    assert "Evaluation" in result.stdout
