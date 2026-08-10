"""Phase 4 — SDK, server, plugins, multi-model, cost optimizer."""

from __future__ import annotations

from pathlib import Path

from openprompt import OpenPrompt, ModelSpec
from openprompt.core.optimizer.cost_optimizer import recommend_cost_quality, pareto_frontier_quality_cost, CostQualityPoint
from openprompt.core.optimizer.multi_model import multi_model_optimize
from openprompt.plugins.discovery import discover_evaluators, discover_strategies
from openprompt.server.app import create_app


def test_openprompt_sdk_facade(examples_dir: Path) -> None:
    client = OpenPrompt(provider="mock")
    report = client.lint(examples_dir / "summarize" / "prompt.txt")
    assert report.score >= 0
    result = client.optimize(examples_dir / "summarize" / "prompt.txt", strategy="rewrite")
    assert result.prompt


def test_multi_model_optimize(examples_dir: Path) -> None:
    client = OpenPrompt(provider="mock")
    result = client.multi_model_optimize(
        examples_dir / "summarize" / "prompt.txt",
        [ModelSpec("mock", "mock-model"), "mock:mock-model"],
        strategy="rewrite",
    )
    assert len(result.results) == 2
    assert "model" in result.to_table_rows()[0]
    assert "|" in result.to_markdown_table()


def test_cost_recommendation(examples_dir: Path) -> None:
    client = OpenPrompt(provider="mock")
    result = client.optimize(examples_dir / "summarize" / "prompt.txt", strategy="rewrite")
    rec = client.recommend_cost_quality(result)
    assert rec.recommended.prompt_id
    assert rec.reason
    assert len(rec.pareto_frontier) >= 1


def test_pareto_frontier():
    points = [
        CostQualityPoint("a", 0.9, 0.10, 100),
        CostQualityPoint("b", 0.85, 0.05, 80),
        CostQualityPoint("c", 0.70, 0.04, 70),
    ]
    frontier = pareto_frontier_quality_cost(points)
    assert len(frontier) >= 1


def test_strategy_plugin_discovery():
    strategies = discover_strategies()
    assert "hybrid" in strategies
    assert "passthrough_rewrite" in strategies


def test_evaluator_plugin_discovery():
    evaluators = discover_evaluators()
    assert "contains" in evaluators
    assert callable(evaluators["contains"])


def test_fastapi_app_creation():
    app = create_app()
    assert app.title == "OpenPrompt API"
    routes = {route.path for route in app.routes}
    assert "/optimize" in routes
    assert "/evaluate" in routes
    assert "/benchmark" in routes
    assert "/lint" in routes
    assert "/compress" in routes
    assert "/multi-model/optimize" in routes
    assert "/cost/recommend" in routes
    assert "/health" in routes
