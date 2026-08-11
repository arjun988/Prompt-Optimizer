"""Build temporary extraction datasets from uploaded files."""

from __future__ import annotations

import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml

ALLOWED_SAMPLE_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff", ".gif", ".bmp", ".txt"}


def _safe_filename(name: str) -> str:
    return Path(name).name.replace("..", "_").strip() or "sample"


@contextmanager
def temp_dataset_from_upload(
    files: list[tuple[str, bytes]],
    *,
    name: str = "upload",
    labels: dict[str, str] | None = None,
    field_schema: dict[str, Any] | None = None,
    example_pool: list[dict[str, Any]] | None = None,
    default_input: str = "Extract structured data from the document.",
) -> Iterator[Path]:
    """Write uploaded samples + labels to a temp dataset directory."""
    if not files:
        raise ValueError("At least one sample file is required.")

    labels = labels or {}
    root = Path(tempfile.mkdtemp(prefix="openprompt_dataset_"))
    samples_dir = root / "samples"
    labels_dir = root / "labels"
    samples_dir.mkdir(parents=True)
    labels_dir.mkdir(parents=True)

    manifest_samples: list[dict[str, Any]] = []
    try:
        for original_name, content in files:
            safe_name = _safe_filename(original_name)
            suffix = Path(safe_name).suffix.lower()
            if suffix not in ALLOWED_SAMPLE_SUFFIXES:
                raise ValueError(
                    f"Unsupported file type: {safe_name}. "
                    f"Allowed: {', '.join(sorted(ALLOWED_SAMPLE_SUFFIXES))}"
                )
            (samples_dir / safe_name).write_bytes(content)
            stem = Path(safe_name).stem
            expected = labels.get(safe_name) or labels.get(stem) or labels.get(original_name)
            if expected:
                (labels_dir / f"{stem}.json").write_text(expected.strip(), encoding="utf-8")

            entry: dict[str, Any] = {
                "name": stem,
                "media": f"samples/{safe_name}",
                "input": default_input,
            }
            if expected:
                entry["expected"] = expected.strip()
            manifest_samples.append(entry)

        inner: dict[str, Any] = {
            "name": name,
            "task": "extraction",
            "samples": manifest_samples,
        }
        if field_schema:
            inner["schema"] = field_schema
        if example_pool:
            pool_path = root / "example_pool.yaml"
            pool_path.write_text(
                yaml.safe_dump({"examples": example_pool}, sort_keys=False),
                encoding="utf-8",
            )
            inner["example_pool"] = "example_pool.yaml"

        manifest = {"dataset": inner}
        (root / "dataset.yaml").write_text(
            yaml.safe_dump(manifest, sort_keys=False),
            encoding="utf-8",
        )
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def parse_labels_json(raw: str | None) -> dict[str, str]:
    if not raw or not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("labels must be a JSON object mapping filename or stem to expected output.")
    return {str(k): str(v) for k, v in data.items()}


def parse_schema_json(raw: str | None) -> dict[str, Any] | None:
    if not raw or not raw.strip():
        return None
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("schema must be a JSON object.")
    return data
