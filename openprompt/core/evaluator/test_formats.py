"""Parse evaluation test suites from JSON and CSV."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any

from openprompt.core.evaluator.metrics import MetricType, TestCase


def parse_tests_json(raw: str | list | dict) -> list[TestCase]:
    """Parse tests from JSON string or object."""
    if isinstance(raw, str):
        data = json.loads(raw)
    else:
        data = raw

    if isinstance(data, dict):
        items = data.get("tests", [])
    elif isinstance(data, list):
        items = data
    else:
        raise ValueError("JSON tests must be an array or an object with a 'tests' array.")

    if not isinstance(items, list):
        raise ValueError("JSON 'tests' must be an array.")

    return [_coerce_test_case(item, index) for index, item in enumerate(items)]


def parse_tests_csv(raw: str) -> list[TestCase]:
    """Parse tests from CSV text. Required columns: input. Optional: name, expected, metric, pattern."""
    text = raw.strip()
    if not text:
        raise ValueError("CSV content is empty.")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV must include a header row.")

    fields = {f.strip().lower() for f in reader.fieldnames if f}
    if "input" not in fields:
        raise ValueError("CSV must include an 'input' column.")

    cases: list[TestCase] = []
    for index, row in enumerate(reader):
        normalized = {k.strip().lower(): (v if v is not None else "") for k, v in row.items() if k}
        input_text = normalized.get("input", "").strip()
        if not input_text:
            continue
        item: dict[str, Any] = {
            "name": normalized.get("name") or f"test_{index + 1}",
            "input": input_text,
            "expected": normalized.get("expected") or None,
            "metric": normalized.get("metric") or "exact_match",
            "pattern": normalized.get("pattern") or None,
        }
        cases.append(_coerce_test_case(item, index))

    if not cases:
        raise ValueError("CSV contained no rows with non-empty input.")
    return cases


def load_test_suite_file(path: Path | str) -> list[TestCase]:
    """Load tests from YAML, JSON, or CSV file."""
    path = Path(path)
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")

    if suffix == ".json":
        return parse_tests_json(text)
    if suffix == ".csv":
        return parse_tests_csv(text)

    from openprompt.core.evaluator.metrics import load_test_suite

    return load_test_suite(path)


def _coerce_test_case(item: Any, index: int) -> TestCase:
    if not isinstance(item, dict):
        raise ValueError(f"Test at index {index} must be a JSON object.")

    input_text = item.get("input")
    if input_text is None:
        raise ValueError(f"Test at index {index} is missing 'input'.")

    metric_raw = item.get("metric", "exact_match")
    if not item.get("metric") and item.get("expected") is not None:
        # Simple input/expected pairs default to exact_match
        metric_raw = "exact_match"

    return TestCase(
        name=str(item.get("name", f"test_{index + 1}")),
        input=str(input_text),
        expected=str(item["expected"]) if item.get("expected") is not None else None,
        metric=MetricType(metric_raw),
        pattern=item.get("pattern"),
        schema=item.get("schema"),
        evaluator=item.get("evaluator"),
        metadata=item.get("metadata") or {},
    )
