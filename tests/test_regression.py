from openprompt.core.evaluator.metrics import EvalReport, TestCase, TestResult, MetricType
from openprompt.core.evaluator.regression import check_regression
from openprompt.config.models import RegressionConfig


def _report(accuracy: float, tokens: int) -> EvalReport:
    return EvalReport(results=[TestResult(TestCase(name="t", input="i", metric=MetricType.EXACT_MATCH), True, accuracy, "o")], prompt_tokens=tokens)


def test_regression_pass() -> None:
    result = check_regression(_report(0.9, 100), _report(0.91, 110), RegressionConfig())
    assert result.passed


def test_regression_fail_on_score_drop() -> None:
    result = check_regression(_report(0.9, 100), _report(0.7, 100), RegressionConfig(min_score_delta=-0.05))
    assert not result.passed


def test_regression_fail_on_token_spike() -> None:
    result = check_regression(_report(0.9, 100), _report(0.91, 200), RegressionConfig(max_token_increase=0.25))
    assert not result.passed
