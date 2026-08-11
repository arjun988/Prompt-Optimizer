"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str


class LintRequest(BaseModel):
    prompt: str


class LintIssueResponse(BaseModel):
    code: str
    message: str
    severity: str
    recommendation: str | None = None


class LintResponse(BaseModel):
    score: int
    issues: list[LintIssueResponse]
    categories: dict[str, int] = Field(default_factory=dict)


class OptimizeRequest(BaseModel):
    prompt: str
    strategy: str | None = "hybrid"
    provider: str = "mock"
    model: str = "mock-model"
    api_key: str | None = None
    tests: list[dict[str, Any]] | None = None
    objective: str | None = None
    constraints: dict[str, Any] | None = None
    eval_budget: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Max evaluation rounds for hybrid/evolutionary/grpo (each round runs every test).",
    )


class OptimizeResponse(BaseModel):
    prompt: str
    original_score: float
    optimized_score: float
    score_delta: float
    original_tokens: int
    optimized_tokens: int
    token_delta_pct: float
    original_cost_usd: float
    optimized_cost_usd: float
    cost_delta_pct: float
    strategy: str
    report_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class EvaluateRequest(BaseModel):
    prompt: str
    provider: str = "mock"
    model: str = "mock-model"
    api_key: str | None = None
    tests: list[dict[str, Any]]


class EvaluateResponse(BaseModel):
    accuracy: float
    pass_rate: float
    prompt_tokens: int
    total_cost_usd: float
    total_latency_ms: float
    judge_score: float | None = None
    warnings: list[str] = Field(default_factory=list)
    results: list[dict[str, Any]]


class BenchmarkRequest(BaseModel):
    prompts: list[str]
    provider: str = "mock"
    model: str = "mock-model"
    api_key: str | None = None


class BenchmarkResponse(BaseModel):
    generated_at: str
    entries: list[dict[str, Any]]
    markdown: str


class CompressRequest(BaseModel):
    prompt: str
    provider: str = "mock"
    model: str = "mock-model"
    api_key: str | None = None


class ModelSpecRequest(BaseModel):
    provider: str
    model: str


class MultiModelOptimizeRequest(BaseModel):
    prompt: str
    models: list[ModelSpecRequest | str]
    strategy: str | None = "rewrite"
    tests: list[dict[str, Any]] | None = None
    provider_keys: dict[str, str] | None = None
    eval_budget: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Max evaluation rounds per model for budgeted strategies.",
    )


class MultiModelOptimizeResponse(BaseModel):
    markdown_table: str
    rows: list[dict[str, Any]]
    best_quality_model: str | None = None
    lowest_cost_model: str | None = None


class CostRecommendRequest(BaseModel):
    prompt: str
    strategy: str = "rewrite"
    provider: str = "mock"
    model: str = "mock-model"
    api_key: str | None = None
    min_quality: float | None = None


class CostRecommendResponse(BaseModel):
    recommended: dict[str, Any]
    pareto_frontier: list[dict[str, Any]]
    reason: str
    quality_per_dollar: float


class DatasetSampleInfo(BaseModel):
    name: str
    media_path: str | None = None
    has_expected: bool = False


class DatasetEvalResponse(BaseModel):
    accuracy: float
    pass_rate: float
    prompt_tokens: int
    total_cost_usd: float
    total_latency_ms: float
    judge_score: float | None = None
    warnings: list[str] = Field(default_factory=list)
    results: list[dict[str, Any]]
    dataset_name: str
    sample_count: int
    samples: list[DatasetSampleInfo] = Field(default_factory=list)


class DatasetOptimizeResponse(BaseModel):
    prompt: str
    original_score: float
    optimized_score: float
    score_delta: float
    original_tokens: int
    optimized_tokens: int
    token_delta_pct: float
    original_cost_usd: float
    optimized_cost_usd: float
    cost_delta_pct: float
    strategy: str
    report_lines: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    dataset_name: str
    sample_count: int
    vision_enabled: bool = False
