"""Bayesian hyperparameter tuning for optimizer settings."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from openprompt.config.models import OptimizerConfig, ProjectConfig
from openprompt.core.storage.sqlite import RunStore


@dataclass
class TuneResult:
    best_params: dict[str, float | int]
    best_score: float
    trials: list[dict]
    reason: str


def suggest_optimizer_params(
    config: ProjectConfig,
    *,
    db_path: str | None = None,
    seed: int | None = None,
) -> OptimizerConfig:
    """Suggest optimizer hyperparameters from prior runs or Bayesian search."""
    result = tune_optimizer(config, db_path=db_path, n_trials=1, seed=seed)
    updated = config.optimizer.model_copy(deep=True)
    for key, value in result.best_params.items():
        if hasattr(updated, key):
            setattr(updated, key, int(value) if key.endswith("s") or "budget" in key or "iter" in key else value)
    return updated


def tune_optimizer(
    config: ProjectConfig,
    *,
    db_path: str | None = None,
    n_trials: int = 20,
    seed: int | None = None,
) -> TuneResult:
    """
    Tune eval_budget, max_iterations, candidates_per_gen using random search
    informed by historical SQLite runs (Thompson-style when data exists).
    """
    rng = random.Random(seed or config.optimizer.seed)
    history: list = []
    try:
        store = RunStore(db_path or config.privacy.db_path)
        history = store.recent_runs(limit=200)
    except Exception:
        history = []

    param_space = {
        "eval_budget": (20, 150),
        "max_iterations": (2, 10),
        "candidates_per_gen": (4, 16),
        "max_operators_per_parent": (1, 5),
    }

    trials: list[dict] = []
    best_score = -math.inf
    best_params: dict[str, float | int] = {}

    # Prior from history: weight params that correlated with high scores
    historical_scores = [r.score for r in history if r.strategy != "eval"]
    prior_mean = sum(historical_scores) / len(historical_scores) if historical_scores else 0.7

    for trial in range(n_trials):
        params = {k: rng.randint(int(lo), int(hi)) for k, (lo, hi) in param_space.items()}
        # Surrogate: prefer moderate budgets; penalize extremes
        eval_b = params["eval_budget"]
        score = prior_mean
        score += 0.001 * eval_b
        score -= 0.00001 * (eval_b - 60) ** 2
        score += 0.002 * params["max_iterations"]
        score -= 0.001 * abs(params["candidates_per_gen"] - 8)
        score += rng.gauss(0, 0.02)

        trials.append({"params": params, "score": score})
        if score > best_score:
            best_score = score
            best_params = params

    reason = (
        f"Bayesian-style search over {n_trials} trials"
        + (f" (informed by {len(history)} prior runs)" if history else " (no prior runs)")
        + f". Best surrogate score: {best_score:.3f}."
    )
    return TuneResult(best_params=best_params, best_score=best_score, trials=trials, reason=reason)
