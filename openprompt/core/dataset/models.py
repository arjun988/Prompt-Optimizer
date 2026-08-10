"""Dataset manifests for extraction prompt optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from openprompt.core.ast.models import ExampleSpec
from openprompt.core.media.loader import load_media


@dataclass
class DatasetSample:
    name: str
    input_text: str = ""
    expected: str | None = None
    media_path: str | None = None
    schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionDataset:
    name: str
    task: str = "extraction"
    field_schema: dict[str, Any] | None = None
    samples: list[DatasetSample] = field(default_factory=list)
    example_pool: list[ExampleSpec] = field(default_factory=list)
    base_dir: Path | None = None


def load_dataset(path: Path | str) -> ExtractionDataset:
    """Load dataset from YAML manifest or directory."""
    path = Path(path)
    if path.is_dir():
        manifest = path / "dataset.yaml"
        if not manifest.exists():
            manifest = path / "dataset.yml"
        if not manifest.exists():
            return _load_dataset_from_directory(path)
        path = manifest

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    root = path.parent
    inner = data.get("dataset", data)

    samples: list[DatasetSample] = []
    for index, item in enumerate(inner.get("samples", [])):
        media_path = item.get("media") or item.get("path")
        resolved = str((root / media_path).resolve()) if media_path else None
        samples.append(
            DatasetSample(
                name=item.get("name", f"sample_{index + 1}"),
                input_text=item.get("input", ""),
                expected=item.get("expected"),
                media_path=resolved,
                schema=item.get("schema"),
                metadata=item.get("metadata", {}),
            )
        )

    pool: list[ExampleSpec] = []
    pool_path = inner.get("example_pool") or inner.get("example_pool_path")
    if pool_path:
        pool = _load_example_pool(root / pool_path)

    return ExtractionDataset(
        name=inner.get("name", path.stem),
        task=inner.get("task", "extraction"),
        field_schema=inner.get("schema") or inner.get("field_schema"),
        samples=samples,
        example_pool=pool,
        base_dir=root,
    )


def dataset_to_test_cases(dataset: ExtractionDataset) -> list:
    """Convert dataset samples to evaluation TestCase list."""
    from openprompt.core.evaluator.metrics import MetricType, TestCase

    cases: list[TestCase] = []
    for sample in dataset.samples:
        input_text = sample.input_text
        if sample.media_path:
            media = load_media(sample.media_path)
            prefix = f"[Document: {media.label}]\n"
            body = media.extracted_text or f"(attached {media.media_type.value}: {media.path})"
            input_text = f"{prefix}{body}\n\n{input_text}".strip()

        metric = MetricType.JSON_SCHEMA if sample.schema or dataset.field_schema else MetricType.EXACT_MATCH
        cases.append(
            TestCase(
                name=sample.name,
                input=input_text or "Extract structured data from the document.",
                expected=sample.expected,
                metric=metric,
                schema=sample.schema or dataset.field_schema,
                metadata=sample.metadata,
            )
        )
    return cases


def _load_example_pool(path: Path) -> list[ExampleSpec]:
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    raw = data.get("examples", data if isinstance(data, list) else [])
    pool: list[ExampleSpec] = []
    for item in raw:
        pool.append(
            ExampleSpec(
                input=item["input"],
                output=item["output"],
                label=item.get("label"),
                difficulty=item.get("difficulty"),
                media_path=item.get("media_path"),
            )
        )
    return pool


def _load_dataset_from_directory(directory: Path) -> ExtractionDataset:
    samples: list[DatasetSample] = []
    labels_dir = directory / "labels"
    for index, media_file in sorted(directory.glob("**/*")):
        if media_file.suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff"}:
            continue
        if media_file.name.startswith("."):
            continue
        expected = None
        label_file = labels_dir / f"{media_file.stem}.json"
        if label_file.exists():
            expected = label_file.read_text(encoding="utf-8").strip()
        samples.append(
            DatasetSample(
                name=media_file.stem,
                media_path=str(media_file.resolve()),
                expected=expected,
            )
        )
    return ExtractionDataset(name=directory.name, samples=samples, base_dir=directory)
