"""Quality/cost Pareto recommendations."""

from __future__ import annotations

from dataclasses import dataclass

from openprompt.core.optimizer.models import CandidateResult, OptimizeResult
from openprompt.core.optimizer.pareto import ObjectiveVector, RankedIndividual, fast_non_dominated_sort, to_ranked


@dataclass
class CostQualityPoint:
    prompt_id: str
    quality: float
    cost_usd: float
    tokens: int
    strategy: str = ""
    operators: str = ""


@dataclass
class CostRecommendation:
    recommended: CostQualityPoint
    pareto_frontier: list[CostQualityPoint]
    reason: str
    quality_per_dollar: float = 0.0


def recommend_cost_quality(
    result: OptimizeResult,
    *,
    min_quality: float | None = None,
    quality_weight: float = 0.7,
    cost_weight: float = 0.3,
) -> CostRecommendation:
    """
    Recommend the best quality/cost tradeoff from optimization candidates.

    Uses Pareto frontier on (quality ↑, cost ↓) then weighted score for final pick.
    """
    points = _collect_points(result)
    if not points:
        raise ValueError("No candidates available for cost recommendation.")

    if min_quality is not None:
        points = [p for p in points if p.quality >= min_quality]
        if not points:
            raise ValueError(f"No candidates meet min_quality={min_quality}.")

    frontier = pareto_frontier_quality_cost(points)
    recommended = _pick_weighted(frontier, quality_weight=quality_weight, cost_weight=cost_weight)
    qpd = recommended.quality / recommended.cost_usd if recommended.cost_usd > 0 else recommended.quality * 1000

    reason = _build_reason(recommended, frontier, result)
    return CostRecommendation(
        recommended=recommended,
        pareto_frontier=frontier,
        reason=reason,
        quality_per_dollar=qpd,
    )


def pareto_frontier_quality_cost(points: list[CostQualityPoint]) -> list[CostQualityPoint]:
    """Return non-dominated points on quality (↑) vs cost (↓)."""
    if len(points) == 1:
        return points

    ranked = to_ranked(
        points,
        lambda p: ObjectiveVector(quality=p.quality, tokens=p.tokens, cost_usd=p.cost_usd),
    )
    fronts = fast_non_dominated_sort(ranked)
    if not fronts:
        return points
    return [ind.item for ind in fronts[0]]


def _collect_points(result: OptimizeResult) -> list[CostQualityPoint]:
    points: list[CostQualityPoint] = [
        CostQualityPoint(
            prompt_id="original",
            quality=result.original_score,
            cost_usd=result.original_cost_usd,
            tokens=result.original_tokens,
            strategy=result.strategy,
        ),
        CostQualityPoint(
            prompt_id="optimized",
            quality=result.optimized_score,
            cost_usd=result.optimized_cost_usd,
            tokens=result.optimized_tokens,
            strategy=result.strategy,
        ),
    ]
    for index, candidate in enumerate(result.candidates):
        points.append(
            CostQualityPoint(
                prompt_id=f"candidate_{index + 1}",
                quality=candidate.quality_score or candidate.score,
                cost_usd=candidate.cost_usd,
                tokens=candidate.tokens,
                strategy=candidate.strategy,
                operators=",".join(candidate.operators_applied),
            )
        )
    return points


def _pick_weighted(
    frontier: list[CostQualityPoint],
    *,
    quality_weight: float,
    cost_weight: float,
) -> CostQualityPoint:
    if not frontier:
        raise ValueError("Empty frontier.")

    max_cost = max(p.cost_usd for p in frontier) or 1.0
    best = frontier[0]
    best_score = -1.0

    for point in frontier:
        cost_norm = 1.0 - (point.cost_usd / max_cost)
        composite = quality_weight * point.quality + cost_weight * cost_norm
        if composite > best_score:
            best_score = composite
            best = point
    return best


def _build_reason(
    recommended: CostQualityPoint,
    frontier: list[CostQualityPoint],
    result: OptimizeResult,
) -> str:
    if recommended.prompt_id == "optimized":
        delta_q = result.score_delta
        delta_c = result.cost_delta_pct
        return (
            f"Optimized prompt recommended: {delta_q:+.1%} quality, {delta_c:+.1f}% cost. "
            f"Pareto frontier size: {len(frontier)}."
        )
    return (
        f"Candidate '{recommended.prompt_id}' is on the quality/cost Pareto frontier "
        f"(quality={recommended.quality:.1%}, cost=${recommended.cost_usd:.4f})."
    )


def recommend_from_candidates(
    candidates: list[CandidateResult],
    *,
    min_quality: float | None = None,
) -> CostRecommendation:
    """Recommend from a raw candidate list."""
    fake = OptimizeResult(
        original= candidates[0].ast,
        optimized=candidates[0].ast,
        original_score=candidates[0].quality_score,
        optimized_score=candidates[0].quality_score,
        original_tokens=candidates[0].tokens,
        optimized_tokens=candidates[0].tokens,
        strategy=candidates[0].strategy,
        candidates=candidates,
        original_cost_usd=candidates[0].cost_usd,
        optimized_cost_usd=candidates[0].cost_usd,
    )
    return recommend_cost_quality(fake, min_quality=min_quality)
