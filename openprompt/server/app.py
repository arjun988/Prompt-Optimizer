"""FastAPI REST server for OpenPrompt."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import yaml

from openprompt import __version__
from openprompt.sdk.client import OpenPrompt
from openprompt.server.schemas import (
    BenchmarkRequest,
    BenchmarkResponse,
    CompressRequest,
    CostRecommendRequest,
    CostRecommendResponse,
    EvaluateRequest,
    EvaluateResponse,
    HealthResponse,
    LintRequest,
    LintResponse,
    MultiModelOptimizeRequest,
    MultiModelOptimizeResponse,
    OptimizeRequest,
    OptimizeResponse,
)


def create_app():
    try:
        from fastapi import FastAPI
    except ImportError as exc:
        raise ImportError("Install server extras: pip install 'openprompt[server]'") from exc

    app = FastAPI(
        title="OpenPrompt API",
        description="REST API for prompt optimization, evaluation, and benchmarking.",
        version=__version__,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    @app.post("/lint", response_model=LintResponse)
    def lint_endpoint(body: LintRequest) -> LintResponse:
        client = OpenPrompt(provider="mock")
        report = client.lint(body.prompt)
        return LintResponse(
            score=report.score,
            categories=report.categories,
            issues=[
                {
                    "code": i.code,
                    "message": i.message,
                    "severity": i.severity.value,
                    "recommendation": i.recommendation,
                }
                for i in report.issues
            ],
        )

    @app.post("/optimize", response_model=OptimizeResponse)
    def optimize_endpoint(body: OptimizeRequest) -> OptimizeResponse:
        client = OpenPrompt(provider=body.provider, model=body.model)
        tests_path = _write_temp_tests(body.tests) if body.tests else None
        result = client.optimize(
            body.prompt,
            strategy=body.strategy,
            tests_path=tests_path,
            objective=body.objective,
            constraints=body.constraints,
        )
        return OptimizeResponse(
            prompt=result.prompt,
            original_score=result.original_score,
            optimized_score=result.optimized_score,
            score_delta=result.score_delta,
            original_tokens=result.original_tokens,
            optimized_tokens=result.optimized_tokens,
            token_delta_pct=result.token_delta_pct,
            original_cost_usd=result.original_cost_usd,
            optimized_cost_usd=result.optimized_cost_usd,
            cost_delta_pct=result.cost_delta_pct,
            strategy=result.strategy,
            report_lines=result.report_lines,
        )

    @app.post("/evaluate", response_model=EvaluateResponse)
    def evaluate_endpoint(body: EvaluateRequest) -> EvaluateResponse:
        client = OpenPrompt(provider=body.provider, model=body.model)
        tests_path = _write_temp_tests(body.tests)
        report = client.evaluate(body.prompt, tests=tests_path)
        return EvaluateResponse(
            accuracy=report.accuracy,
            pass_rate=report.pass_rate,
            prompt_tokens=report.prompt_tokens,
            total_cost_usd=report.total_cost_usd,
            total_latency_ms=report.total_latency_ms,
            judge_score=report.judge_score,
            results=[
                {
                    "name": r.test.name,
                    "passed": r.passed,
                    "score": r.score,
                    "message": r.message,
                }
                for r in report.results
            ],
        )

    @app.post("/benchmark", response_model=BenchmarkResponse)
    def benchmark_endpoint(body: BenchmarkRequest) -> BenchmarkResponse:
        client = OpenPrompt(provider=body.provider, model=body.model)
        paths = _write_temp_prompts(body.prompts)
        report = client.benchmark(paths)
        return BenchmarkResponse(
            generated_at=report.generated_at,
            entries=[e.__dict__ for e in report.entries],
            markdown=report.to_markdown(),
        )

    @app.post("/compress", response_model=OptimizeResponse)
    def compress_endpoint(body: CompressRequest) -> OptimizeResponse:
        client = OpenPrompt(provider=body.provider, model=body.model)
        result = client.compress(body.prompt)
        return OptimizeResponse(
            prompt=result.prompt,
            original_score=result.original_score,
            optimized_score=result.optimized_score,
            score_delta=result.score_delta,
            original_tokens=result.original_tokens,
            optimized_tokens=result.optimized_tokens,
            token_delta_pct=result.token_delta_pct,
            original_cost_usd=result.original_cost_usd,
            optimized_cost_usd=result.optimized_cost_usd,
            cost_delta_pct=result.cost_delta_pct,
            strategy=result.strategy,
            report_lines=result.report_lines,
        )

    @app.post("/multi-model/optimize", response_model=MultiModelOptimizeResponse)
    def multi_model_endpoint(body: MultiModelOptimizeRequest) -> MultiModelOptimizeResponse:
        client = OpenPrompt(provider="mock")
        tests_path = _write_temp_tests(body.tests) if body.tests else None
        models = [m if isinstance(m, str) else f"{m.provider}:{m.model}" for m in body.models]
        result = client.multi_model_optimize(
            body.prompt,
            models,
            strategy=body.strategy,
            tests_path=tests_path,
        )
        best_q = result.best_quality
        best_c = result.lowest_cost
        return MultiModelOptimizeResponse(
            markdown_table=result.to_markdown_table(),
            rows=result.to_table_rows(),
            best_quality_model=best_q.spec.label if best_q else None,
            lowest_cost_model=best_c.spec.label if best_c else None,
        )

    @app.post("/cost/recommend", response_model=CostRecommendResponse)
    def cost_recommend_endpoint(body: CostRecommendRequest) -> CostRecommendResponse:
        client = OpenPrompt(provider=body.provider, model=body.model)
        result = client.optimize(body.prompt, strategy=body.strategy)
        rec = client.recommend_cost_quality(result, min_quality=body.min_quality)
        return CostRecommendResponse(
            recommended=rec.recommended.__dict__,
            pareto_frontier=[p.__dict__ for p in rec.pareto_frontier],
            reason=rec.reason,
            quality_per_dollar=rec.quality_per_dollar,
        )

    return app


def _write_temp_tests(tests: list[dict[str, Any]] | None) -> Path | None:
    if not tests:
        return None
    fd, name = tempfile.mkstemp(suffix=".yaml")
    import os

    os.close(fd)
    path = Path(name)
    path.write_text(yaml.safe_dump({"tests": tests}), encoding="utf-8")
    return path


def _write_temp_prompts(prompts: list[str]) -> list[Path]:
    import os

    paths: list[Path] = []
    for index, text in enumerate(prompts):
        fd, name = tempfile.mkstemp(suffix=f"_{index}.txt")
        os.close(fd)
        path = Path(name)
        path.write_text(text, encoding="utf-8")
        paths.append(path)
    return paths
