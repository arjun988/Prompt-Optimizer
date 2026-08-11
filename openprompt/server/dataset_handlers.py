"""Shared handlers for dataset eval/optimize (CLI + REST)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openprompt.core.ast.models import DatasetRef, OutputFormat, OutputSpec, PromptAST
from openprompt.core.dataset.models import dataset_to_test_cases, load_dataset
from openprompt.core.evaluator.metrics import EvalReport, run_evaluation
from openprompt.core.media.loader import load_media
from openprompt.core.optimizer.models import OptimizeResult
from openprompt.core.parser.parser import parse_any, parse_file
from openprompt.plugins.discovery import discover_evaluators
from openprompt.providers.base import create_provider
from openprompt.sdk.client import OpenPrompt


def prepare_extraction_ast(
    prompt: str | Path,
    dataset_path: Path,
    *,
    vision: bool = False,
) -> tuple[PromptAST, Any]:
    """Parse prompt and attach dataset + optional vision media."""
    ds = load_dataset(dataset_path)
    prompt_path = Path(prompt)
    if isinstance(prompt, Path) or (isinstance(prompt, str) and prompt_path.is_file()):
        ast = parse_file(prompt_path)
    else:
        ast = parse_any(str(prompt))

    if ds.field_schema and (not ast.output or not ast.output.schema_):
        ast.output = OutputSpec(format=OutputFormat.JSON, schema=ds.field_schema)

    manifest_path = dataset_path / "dataset.yaml" if dataset_path.is_dir() else dataset_path
    ast.dataset = ast.dataset or DatasetRef(
        path=str(manifest_path.resolve()),
        name=ds.name,
        field_schema=ds.field_schema,
    )

    if vision and ds.samples and ds.samples[0].media_path:
        ast.media = [load_media(ds.samples[0].media_path, use_vision=True)]

    return ast, ds


def run_dataset_eval(
    prompt: str | Path,
    dataset_path: Path,
    *,
    provider: str = "mock",
    model: str = "mock-model",
    pass_threshold: float = 0.85,
    api_key: str | None = None,
) -> tuple[EvalReport, dict[str, Any]]:
    ast, ds = prepare_extraction_ast(prompt, dataset_path, vision=False)
    tests = dataset_to_test_cases(ds)
    model_provider = create_provider(provider, model, api_key=api_key)
    report = run_evaluation(
        ast,
        tests,
        model_provider,
        plugin_evaluators=discover_evaluators(),
        provider_name=provider,
        model_name=model,
        pass_threshold=pass_threshold,
    )
    meta = {
        "dataset_name": ds.name,
        "sample_count": len(ds.samples),
        "samples": [
            {
                "name": s.name,
                "media_path": s.media_path,
                "has_expected": bool(s.expected),
            }
            for s in ds.samples
        ],
    }
    return report, meta


def run_dataset_optimize(
    prompt: str | Path,
    dataset_path: Path,
    *,
    provider: str = "mock",
    model: str = "mock-model",
    strategy: str = "extraction",
    vision: bool = False,
    api_key: str | None = None,
) -> OptimizeResult:
    ast, _ds = prepare_extraction_ast(prompt, dataset_path, vision=vision)
    client = OpenPrompt(provider=provider, model=model, api_key=api_key, warn_mock=False)
    return client.optimize(ast, strategy=strategy)
