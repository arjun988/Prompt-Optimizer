"""OpenPrompt CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from openprompt import __version__
from openprompt.config.models import default_init_config, find_project_config
from openprompt.core.ast.models import PromptAST
from openprompt.core.benchmark.runner import benchmark_paths, compare_prompts
from openprompt.core.compiler.renderer import ast_to_yaml_dict, render_generic
from openprompt.core.evaluator.custom import load_custom_evaluator
from openprompt.core.evaluator.metrics import load_test_suite, resolve_test_suite, run_evaluation
from openprompt.core.evaluator.regression import check_regression
from openprompt.core.linter.linter import lint
from openprompt.core.optimizer.engine import Optimizer
from openprompt.core.parser.parser import parse_file
from openprompt.core.security.scanner import scan
from openprompt.core.storage.sqlite import RunStore
from openprompt.core.versioning.diff import diff_files, save_version
from openprompt.providers.base import create_provider

app = typer.Typer(
    name="openprompt",
    help="Open-source prompt optimizer — analyze, optimize, evaluate, benchmark.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def init(
    project: str = typer.Option("my-project", "--project", "-p", help="Project name."),
    path: Path = typer.Option(Path("."), "--path", help="Directory to initialize."),
) -> None:
    """Create openprompt.yaml, prompts/, tests/, and evaluators/."""
    root = path.resolve()
    config = default_init_config(project)
    config.save(root / "openprompt.yaml")

    (root / "prompts").mkdir(exist_ok=True)
    (root / "tests").mkdir(exist_ok=True)
    (root / "evaluators").mkdir(exist_ok=True)

    sample_prompt = root / "prompts" / "example.txt"
    if not sample_prompt.exists():
        sample_prompt.write_text(
            "Summarize the following article in 5-7 bullet points.\n",
            encoding="utf-8",
        )

    sample_tests = root / "tests" / "example_tests.yaml"
    if not sample_tests.exists():
        sample_tests.write_text(
            yaml.safe_dump(
                {
                    "tests": [
                        {
                            "name": "non_empty",
                            "input": "AI is transforming software development.",
                            "metric": "contains",
                            "expected": "-",
                        }
                    ]
                },
                sort_keys=False,
            ),
            encoding="utf-8",
        )

    console.print(f"[green]✓[/green] Initialized OpenPrompt project in {root}")
    console.print("  openprompt.yaml")
    console.print("  prompts/")
    console.print("  tests/")
    console.print("  evaluators/")


@app.command()
def lint(
    prompt: Path = typer.Argument(..., help="Prompt file (.txt, .yaml, .yml)."),
) -> None:
    """Analyze a prompt for quality issues (offline)."""
    ast = parse_file(prompt)
    report = lint(ast)

    console.print("\n[bold]Prompt Analysis[/bold]")
    console.print("─" * 40)
    for issue in report.issues:
        if issue.severity.value == "ok":
            console.print(f"[green]{issue.symbol}[/green] {issue.message}")
        elif issue.severity.value == "error":
            console.print(f"[red]{issue.symbol}[/red] {issue.message}")
        else:
            console.print(f"[yellow]{issue.symbol}[/yellow] {issue.message}")
        if issue.recommendation and issue.severity.value != "ok":
            console.print(f"   [dim]→ {issue.recommendation}[/dim]")

    console.print(f"\n[bold]Score:[/bold] {report.score}/100 [dim](heuristic — run eval for measured score)[/dim]")


@app.command()
def inspect(
    prompt: Path = typer.Argument(..., help="Prompt file to inspect."),
    format: str = typer.Option("yaml", "--format", "-f", help="Output format: yaml, json, text."),
) -> None:
    """Parse a prompt and show its AST (offline)."""
    ast = parse_file(prompt)
    if format == "json":
        console.print_json(json.dumps(ast_to_yaml_dict(ast)["prompt"], indent=2))
    elif format == "text":
        console.print(render_generic(ast))
    else:
        console.print(yaml.safe_dump(ast_to_yaml_dict(ast), sort_keys=False, allow_unicode=True))


@app.command("eval")
def eval_cmd(
    target: Path = typer.Argument(..., help="Prompt file or directory with tests."),
    tests: Optional[Path] = typer.Option(None, "--tests", "-t", help="Path to test suite YAML."),
    provider: Optional[str] = typer.Option(None, "--provider", help="Model provider."),
    model: Optional[str] = typer.Option(None, "--model", help="Model name."),
    baseline: Optional[str] = typer.Option(None, "--baseline", help="Baseline prompt path for regression."),
    fail_on_regression: bool = typer.Option(False, "--fail-on-regression", help="Exit 1 on regression."),
) -> None:
    """Evaluate a prompt against test cases."""
    config = find_project_config()
    if provider:
        config.model.provider = provider
    if model:
        config.model.name = model

    model_provider = create_provider(config.model.provider, config.model.name)

    if target.is_dir():
        prompt_files = list(target.glob("*.yaml")) + list(target.glob("*.yml")) + list(target.glob("*.txt"))
        if not prompt_files:
            console.print("[red]No prompt files found in directory.[/red]")
            raise typer.Exit(1)
        prompt_path = prompt_files[0]
        tests_path = tests or (target / "tests.yaml")
    else:
        prompt_path = target
        tests_path = tests or resolve_test_suite(target)

    if not tests_path or not tests_path.exists():
        console.print(f"[red]Test suite not found for {target}[/red]")
        raise typer.Exit(1)

    ast = parse_file(prompt_path)
    tests = load_test_suite(tests_path)

    judge_provider = None
    if config.evaluation.judge:
        j = config.evaluation.judge
        judge_provider = create_provider(j.provider, j.model)

    custom_eval_fn = None
    if config.evaluation.custom_evaluator:
        custom_eval_fn = load_custom_evaluator(config.evaluation.custom_evaluator)

    report = run_evaluation(
        ast,
        tests,
        model_provider,
        judge_provider=judge_provider,
        custom_eval_fn=custom_eval_fn,
    )

    console.print("\n[bold]Evaluation[/bold]")
    console.print("─" * 40)
    console.print(f"Accuracy:  [bold]{report.accuracy:.1%}[/bold]")
    console.print(f"Pass rate: {report.pass_rate:.1%}")
    console.print(f"Tests:     {len(report.results)}")

    for result in report.results:
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(f"  {status} {result.test.name}: {result.message}")

    if config.privacy.storage == "local":
        store = RunStore(config.privacy.db_path)
        store.log_run(
            prompt_name=prompt_path.stem,
            strategy="eval",
            model=config.model.name,
            score=report.accuracy,
            tokens=report.prompt_tokens,
        )

    if baseline:
        baseline_ast = parse_file(baseline)
        baseline_report = run_evaluation(baseline_ast, tests, model_provider)
        regression = check_regression(baseline_report, report, config.regression)
        console.print("\n[bold]Regression Check[/bold]")
        for msg in regression.messages:
            icon = "[green]✓[/green]" if regression.passed else "[red]✗[/red]"
            console.print(f"  {icon} {msg}")
        if fail_on_regression and not regression.passed:
            raise typer.Exit(1)


@app.command()
def optimize(
    prompt: Path = typer.Argument(..., help="Prompt file to optimize."),
    strategy: Optional[str] = typer.Option(None, "--strategy", "-s", help="Optimization strategy."),
    provider: Optional[str] = typer.Option(None, "--provider", help="Model provider."),
    model: Optional[str] = typer.Option(None, "--model", help="Model name."),
    tests: Optional[Path] = typer.Option(None, "--tests", help="Path to test suite."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Save optimized prompt."),
) -> None:
    """Optimize a prompt using the configured strategy."""
    config = find_project_config()
    if provider:
        config.model.provider = provider
    if model:
        config.model.name = model
    if strategy:
        config.optimizer.strategy = strategy  # type: ignore[assignment]

    optimizer = Optimizer(
        provider=config.model.provider,
        model=config.model.name,
        config=config,
    )

    console.print("[dim]Analyzing prompt...[/dim]")
    result = optimizer.optimize(prompt, strategy=strategy, tests_path=tests)

    if result.lint_report:
        for issue in result.lint_report.issues:
            if issue.severity.value in {"error", "warning"}:
                console.print(f"  [yellow]⚠[/yellow] {issue.message}")

    console.print("[green]✓[/green] Optimization complete\n")

    table = Table(title="Results")
    table.add_column("Metric")
    table.add_column("Original")
    table.add_column("Optimized")
    table.add_column("Delta")
    table.add_row("Score", f"{result.original_score:.1%}", f"{result.optimized_score:.1%}", f"{result.score_delta:+.1%}")
    table.add_row("Tokens", str(result.original_tokens), str(result.optimized_tokens), f"{result.token_delta_pct:+.1f}%")
    table.add_row("Strategy", result.strategy, "", "")
    console.print(table)

    if result.candidates:
        console.print("\n[bold]Top candidates[/bold]")
        for candidate in sorted(result.candidates, key=lambda c: -c.score)[:5]:
            console.print(
                f"  {candidate.score:.1%}  ({candidate.tokens} tokens)  "
                f"[dim]{', '.join(candidate.operators_applied) or 'baseline'}[/dim]"
            )

    console.print("\n[bold]Recommended Prompt[/bold]")
    console.print("─" * 40)
    console.print(Panel(result.prompt, border_style="green"))

    if result.failure_analyses:
        console.print("\n[bold]Failure Analysis[/bold]")
        for fa in result.failure_analyses[:5]:
            console.print(f"  [red]✗[/red] {fa.test_name}: {fa.category}")
            console.print(f"     [dim]→ {fa.recommendation} ({fa.recommended_operator})[/dim]")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix in {".yaml", ".yml"}:
            data = ast_to_yaml_dict(result.optimized)
            output.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
        else:
            output.write_text(result.prompt, encoding="utf-8")
        console.print(f"\n[green]✓[/green] Saved to {output}")

    if config.privacy.storage == "local":
        store = RunStore(config.privacy.db_path)
        store.log_run(
            prompt_name=prompt.stem,
            strategy=result.strategy,
            model=config.model.name,
            score=result.optimized_score,
            tokens=result.optimized_tokens,
            metadata={"original_score": result.original_score},
        )


@app.command()
def compress(
    prompt: Path = typer.Argument(..., help="Prompt file to compress."),
    provider: Optional[str] = typer.Option(None, "--provider"),
    model: Optional[str] = typer.Option(None, "--model"),
    output: Optional[Path] = typer.Option(None, "--output", "-o"),
) -> None:
    """Compress a prompt while preserving quality."""
    config = find_project_config()
    if provider:
        config.model.provider = provider
    if model:
        config.model.name = model
    config.optimizer.strategy = "compress"

    optimizer = Optimizer(provider=config.model.provider, model=config.model.name, config=config)
    result = optimizer.optimize(prompt, strategy="compress")

    reduction = -result.token_delta_pct
    console.print(f"[bold]Compression[/bold]: {result.original_tokens} → {result.optimized_tokens} tokens ({reduction:.1f}% reduction)")
    console.print(Panel(result.prompt))

    if output:
        output.write_text(result.prompt, encoding="utf-8")
        console.print(f"[green]✓[/green] Saved to {output}")


@app.command()
def benchmark(
    path: Path = typer.Argument(..., help="Directory or file with prompts."),
    provider: Optional[str] = typer.Option(None, "--provider"),
    model: Optional[str] = typer.Option(None, "--model"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write markdown report."),
) -> None:
    """Benchmark prompts in a directory."""
    config = find_project_config()
    if provider:
        config.model.provider = provider
    if model:
        config.model.name = model

    model_provider = create_provider(config.model.provider, config.model.name)

    if path.is_dir():
        files = sorted(path.glob("**/*.yaml")) + sorted(path.glob("**/*.yml")) + sorted(path.glob("**/*.txt"))
    else:
        files = [path]

    if not files:
        console.print("[red]No prompt files found.[/red]")
        raise typer.Exit(1)

    report = benchmark_paths(files, model_provider, tests_dir=path if path.is_dir() else path.parent)
    md = report.to_markdown()
    console.print(md)

    if output:
        output.write_text(md, encoding="utf-8")
        json_path = output.with_suffix(".json")
        json_path.write_text(report.to_json(), encoding="utf-8")
        console.print(f"[green]✓[/green] Report saved to {output}")


@app.command()
def compare(
    prompt_a: Path = typer.Argument(..., help="First prompt."),
    prompt_b: Path = typer.Argument(..., help="Second prompt."),
    tests: Path = typer.Argument(..., help="Test suite YAML."),
    provider: Optional[str] = typer.Option(None, "--provider"),
    model: Optional[str] = typer.Option(None, "--model"),
) -> None:
    """Compare two prompts on the same test suite."""
    config = find_project_config()
    if provider:
        config.model.provider = provider
    if model:
        config.model.name = model

    model_provider = create_provider(config.model.provider, config.model.name)
    ast_a = parse_file(prompt_a)
    ast_b = parse_file(prompt_b)
    test_cases = load_test_suite(tests)

    result = compare_prompts(ast_a, ast_b, model_provider, test_cases)
    console.print("\n[bold]Comparison[/bold]")
    console.print(f"  A accuracy: {result['a']['accuracy']:.1%}  ({result['a']['tokens']} tokens)")
    console.print(f"  B accuracy: {result['b']['accuracy']:.1%}  ({result['b']['tokens']} tokens)")
    console.print(f"  Δ accuracy: {result['delta_accuracy']:+.1%}")
    console.print(f"  Δ tokens:   {result['delta_tokens']:+d}")


@app.command()
def security(
    prompt: Path = typer.Argument(..., help="Prompt file to scan."),
) -> None:
    """Scan a prompt for security issues (offline)."""
    ast = parse_file(prompt)
    report = scan(ast)

    console.print("\n[bold]Security Analysis[/bold]")
    console.print("─" * 40)
    for finding in report.findings:
        color = {"critical": "red", "high": "red", "medium": "yellow", "low": "yellow", "info": "green"}.get(
            finding.severity, "white"
        )
        console.print(f"[{color}]●[/{color}] [{finding.severity}] {finding.message}")
        if finding.recommendation:
            console.print(f"   [dim]→ {finding.recommendation}[/dim]")
    console.print(f"\n[bold]Security score:[/bold] {report.score}/100")


@app.command()
def diff(
    a: Path = typer.Argument(..., help="First prompt or version file."),
    b: Path = typer.Argument(..., help="Second prompt or version file."),
) -> None:
    """Diff two prompt versions."""
    result = diff_files(a, b)
    console.print("\n[bold]Prompt Diff[/bold]")
    console.print("─" * 40)
    console.print(result.to_text())


@app.command()
def save(
    prompt: Path = typer.Argument(..., help="Prompt to save as version."),
    version: str = typer.Argument(..., help="Version label (e.g. v1, v2)."),
    directory: Path = typer.Option(Path("prompts/versions"), "--dir", help="Version directory."),
) -> None:
    """Save a prompt as a versioned YAML file."""
    ast = parse_file(prompt)
    path = save_version(ast, directory, version)
    console.print(f"[green]✓[/green] Saved {path}")


@app.command()
def template(
    name: str = typer.Argument(..., help="Template name."),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write to file."),
) -> None:
    """Print a built-in prompt template."""
    from importlib.resources import files

    normalized = name.replace("-", "_")
    pkg = files("openprompt.templates")
    template_path = pkg / f"{normalized}.yaml"
    if not template_path.is_file():
        available = [p.name.replace(".yaml", "") for p in pkg.iterdir() if p.name.endswith(".yaml")]
        console.print(f"[red]Unknown template: {name}[/red]")
        console.print(f"Available: {', '.join(sorted(available))}")
        raise typer.Exit(1)

    content = template_path.read_text(encoding="utf-8")
    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]✓[/green] Template written to {output}")
    else:
        console.print(content)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"openprompt {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", "-V", callback=_version_callback, is_eager=True),
) -> None:
    """OpenPrompt CLI."""
