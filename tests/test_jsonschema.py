"""JSON schema validation tests."""

from openprompt.core.evaluator.metrics import validate_json_schema


def test_nested_schema_validation() -> None:
    schema = {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}, "count": {"type": "number"}},
                },
            }
        },
    }
    valid = {"items": [{"name": "a", "count": 1}]}
    assert validate_json_schema(valid, schema) == []

    invalid = {"items": [{"count": 1}]}
    errors = validate_json_schema(invalid, schema)
    assert errors


def test_plugin_evaluator_by_name() -> None:
    from openprompt.core.evaluator.metrics import MetricType, TestCase, score_output

    test = TestCase(name="t", input="x", expected="hello", metric=MetricType.EXACT_MATCH, evaluator="contains")
    from openprompt.plugins.discovery import discover_evaluators

    score, msg = score_output("hello world", test, plugin_evaluators=discover_evaluators())
    assert score == 1.0
