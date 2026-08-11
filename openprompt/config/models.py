"""Project and runtime configuration models."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ModelConfig(BaseModel):
    provider: str = "mock"
    name: str = "mock-model"
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4096


class MultiModelEntry(BaseModel):
    provider: str
    model: str


class MetaModelConfig(BaseModel):
    """Cheap model that proposes prompt mutations (GRPO proposer)."""

    provider: str = "openai"
    model: str = "gpt-5.6-luna"


class OptimizerConfig(BaseModel):
    strategy: Literal[
        "rewrite",
        "iterative",
        "evolutionary",
        "hybrid",
        "compress",
        "rag",
        "agent",
        "grpo",
        "few_shot",
        "extraction",
    ] = "hybrid"
    max_iterations: int = 5
    candidates_per_gen: int = 8
    eval_budget: int = 100
    seed: int | None = None
    compress_min_quality_ratio: float = 0.98
    require_tests_for_claims: bool = True
    max_operators_per_parent: int = 3
    parallel_workers: int = 4
    few_shot_count: int = 3
    grpo_proposals: int = 4
    auto_tune: bool = False


class JudgeConfig(BaseModel):
    provider: str = "mock"
    model: str = "mock-model"
    rubric: str | None = None


class EvaluationConfig(BaseModel):
    metrics: list[str] = Field(default_factory=lambda: ["exact_match"])
    judge: JudgeConfig | None = None
    custom_evaluator: str | None = None
    pass_threshold: float = 0.85
    min_test_count: int = 3
    holdout_ratio: float = 0.0
    example_pool_path: str | None = None
    dataset_path: str | None = None


class ServerConfig(BaseModel):
    api_key: str | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    rate_limit_per_minute: int = 120
    host: str = "127.0.0.1"
    port: int = 8000
    public_paths: list[str] = Field(default_factory=lambda: ["/health", "/docs", "/openapi.json", "/redoc"])

    @property
    def public_paths_set(self) -> set[str]:
        return set(self.public_paths)

    @classmethod
    def from_env(cls) -> ServerConfig:
        import os

        api_key = os.environ.get("OPENPROMPT_API_KEY") or os.environ.get("OPENPROMPT_SERVER_API_KEY")
        cors = os.environ.get("OPENPROMPT_CORS_ORIGINS")
        origins = [o.strip() for o in cors.split(",")] if cors else ["http://localhost:3000", "http://127.0.0.1:3000"]
        rate = int(os.environ.get("OPENPROMPT_RATE_LIMIT", "120"))
        return cls(api_key=api_key, cors_origins=origins, rate_limit_per_minute=rate)


class ObjectivesConfig(BaseModel):
    quality_weight: float = 1.0
    token_weight: float = 0.3
    cost_weight: float = 0.2
    latency_weight: float = 0.0


class PrivacyConfig(BaseModel):
    telemetry: bool = False
    storage: Literal["local", "none"] = "local"
    db_path: str = ".openprompt/runs.db"


class RegressionConfig(BaseModel):
    min_score_delta: float = -0.05
    max_token_increase: float = 0.25


class ProjectConfig(BaseModel):
    project: str = "my-project"
    model: ModelConfig = Field(default_factory=ModelConfig)
    models: list[MultiModelEntry] = Field(default_factory=list)
    meta_model: MetaModelConfig | None = None
    optimizer: OptimizerConfig = Field(default_factory=OptimizerConfig)
    evaluation: EvaluationConfig = Field(default_factory=EvaluationConfig)
    objectives: ObjectivesConfig = Field(default_factory=ObjectivesConfig)
    privacy: PrivacyConfig = Field(default_factory=PrivacyConfig)
    regression: RegressionConfig = Field(default_factory=RegressionConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    def model_copy_deep(self) -> ProjectConfig:
        return self.model_copy(deep=True)

    @classmethod
    def load(cls, path: Path | str) -> ProjectConfig:
        path = Path(path)
        if not path.exists():
            return cls()
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls.model_validate(data)

    def save(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(self.model_dump(mode="json"), sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


class EnvSettings(BaseSettings):
    """Environment variable overrides."""

    model_config = SettingsConfigDict(env_prefix="OPENPROMPT_", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    ollama_host: str | None = Field(default=None, alias="OLLAMA_HOST")
    openrouter_api_key: str | None = Field(default=None, alias="OPENROUTER_API_KEY")
    xai_api_key: str | None = Field(default=None, alias="XAI_API_KEY")
    google_api_key: str | None = Field(default=None, alias="GOOGLE_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")


def find_project_config(start: Path | None = None) -> ProjectConfig:
    """Walk up from *start* looking for openprompt.yaml."""
    current = (start or Path.cwd()).resolve()
    for directory in [current, *current.parents]:
        config_path = directory / "openprompt.yaml"
        if config_path.exists():
            return ProjectConfig.load(config_path)
    return ProjectConfig()


def default_init_config(project_name: str = "my-project") -> ProjectConfig:
    return ProjectConfig(project=project_name)
