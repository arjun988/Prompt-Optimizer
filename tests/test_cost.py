from openprompt.core.cost.pricing import estimate_cost_usd, estimate_tokens_cost_usd
from openprompt.providers.base import ModelResponse


def test_mock_cost_zero() -> None:
    response = ModelResponse(content="hi", model="mock-model", input_tokens=100, output_tokens=50)
    assert estimate_cost_usd(response, provider="mock", model="mock-model") == 0.0


def test_openai_cost_positive() -> None:
    cost = estimate_tokens_cost_usd(1000, 500, provider="openai", model="gpt-4o")
    assert cost > 0
