"""Multi-model prompt optimization."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from openprompt.config.models import ProjectConfig
from openprompt.core.compiler.renderer import render_generic, render_messages
from openprompt.core.optimizer.engine import Optimizer
from openprompt.core.optimizer.models import OptimizeResult


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass
class ModelOptimizeResult:
    spec: ModelSpec
    result: OptimizeResult
    rendered_prompt: str
    message_count: int = 0


@dataclass
class MultiModelOptimizeResult:
    results: list[ModelOptimizeResult] = field(default_factory=list)

    @property
    def best_quality(self) -> ModelOptimizeResult | None:
        if not self.results:
            return None
        return max(self.results, key=lambda r: r.result.optimized_score)

    @property
    def lowest_cost(self) -> ModelOptimizeResult | None:
        if not self.results:
            return None
        return min(self.results, key=lambda r: r.result.optimized_cost_usd)

    def to_table_rows(self) -> list[dict[str, str | float | int]]:
        rows: list[dict[str, str | float | int]] = []
        for item in self.results:
            rows.append(
                {
                    "model": item.spec.label,
                    "provider": item.spec.provider,
                    "original_score": round(item.result.original_score, 4),
                    "optimized_score": round(item.result.optimized_score, 4),
                    "score_delta": round(item.result.score_delta, 4),
                    "original_tokens": item.result.original_tokens,
                    "optimized_tokens": item.result.optimized_tokens,
                    "original_cost_usd": round(item.result.original_cost_usd, 6),
                    "optimized_cost_usd": round(item.result.optimized_cost_usd, 6),
                    "strategy": item.result.strategy,
                }
            )
        return rows

    def to_markdown_table(self) -> str:
        rows = self.to_table_rows()
        if not rows:
            return "No results."
        headers = list(rows[0].keys())
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
        return "\n".join(lines)


def multi_model_optimize(
    prompt: str | Path,
    models: list[ModelSpec],
    *,
    config: ProjectConfig | None = None,
    strategy: str | None = None,
    tests_path: str | Path | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> MultiModelOptimizeResult:
    """Optimize the same prompt across multiple models and compare."""
    output = MultiModelOptimizeResult()

    for spec in models:
        optimizer = Optimizer(
            provider=spec.provider,
            model=spec.model,
            config=config,
            api_key=api_key,
            base_url=base_url,
        )
        result = optimizer.optimize(prompt, strategy=strategy, tests_path=tests_path)
        rendered = render_generic(result.optimized)
        messages = render_messages(result.optimized, provider=_map_provider_format(spec.provider))
        output.results.append(
            ModelOptimizeResult(
                spec=spec,
                result=result,
                rendered_prompt=rendered,
                message_count=len(messages),
            )
        )

    return output


def _map_provider_format(provider: str) -> str:
    if provider in {"openai", "grok", "ollama", "mock"}:
        return "openai"
    if provider == "anthropic":
        return "anthropic"
    if provider == "gemini":
        return "gemini"
    return "generic"
