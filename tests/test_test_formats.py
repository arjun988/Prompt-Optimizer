import json
from pathlib import Path

import pytest

from openprompt.core.evaluator.metrics import MetricType, load_test_suite
from openprompt.core.evaluator.test_formats import parse_tests_csv, parse_tests_json


def test_parse_tests_json_array() -> None:
    raw = json.dumps(
        [
            {"input": "hello", "expected": "hello"},
            {"name": "contains_x", "input": "abc", "expected": "b", "metric": "contains"},
        ]
    )
    cases = parse_tests_json(raw)
    assert len(cases) == 2
    assert cases[0].input == "hello"
    assert cases[0].metric == MetricType.EXACT_MATCH
    assert cases[1].name == "contains_x"
    assert cases[1].metric == MetricType.CONTAINS


def test_parse_tests_json_object_with_tests_key() -> None:
    raw = json.dumps({"tests": [{"input": "x", "expected": "y"}]})
    cases = parse_tests_json(raw)
    assert len(cases) == 1
    assert cases[0].expected == "y"


def test_parse_tests_json_missing_input_raises() -> None:
    with pytest.raises(ValueError, match="missing 'input'"):
        parse_tests_json(json.dumps([{"expected": "x"}]))


def test_parse_tests_csv() -> None:
    raw = """name,input,expected,metric
t1,"Hello world",hello,contains
t2,plain text,plain,exact_match
"""
    cases = parse_tests_csv(raw)
    assert len(cases) == 2
    assert cases[0].name == "t1"
    assert cases[0].input == "Hello world"
    assert cases[0].metric == MetricType.CONTAINS
    assert cases[1].expected == "plain"


def test_parse_tests_csv_requires_input_column() -> None:
    with pytest.raises(ValueError, match="input"):
        parse_tests_csv("name,expected\na,b\n")


def test_load_test_suite_json_file(tmp_path: Path) -> None:
    path = tmp_path / "tests.json"
    path.write_text(
        json.dumps([{"input": "foo", "expected": "bar"}]),
        encoding="utf-8",
    )
    cases = load_test_suite(path)
    assert len(cases) == 1
    assert cases[0].input == "foo"


def test_load_test_suite_csv_file(tmp_path: Path) -> None:
    path = tmp_path / "tests.csv"
    path.write_text("input,expected\nfoo,bar\n", encoding="utf-8")
    cases = load_test_suite(path)
    assert len(cases) == 1
    assert cases[0].expected == "bar"


def test_load_test_suite_yaml_still_works(examples_dir: Path) -> None:
    cases = load_test_suite(examples_dir / "summarize" / "tests.yaml")
    assert len(cases) == 3
