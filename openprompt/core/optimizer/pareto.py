"""NSGA-II multi-objective selection for prompt optimization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class ObjectiveVector:
    """Objectives: maximize quality, minimize tokens, minimize cost."""

    quality: float
    tokens: int
    cost_usd: float

    def dominates(self, other: ObjectiveVector) -> bool:
        """True if self Pareto-dominates other (all ≥ and at least one > for max objectives)."""
        better_quality = self.quality >= other.quality
        better_tokens = self.tokens <= other.tokens
        better_cost = self.cost_usd <= other.cost_usd
        strictly_better = (
            self.quality > other.quality
            or self.tokens < other.tokens
            or self.cost_usd < other.cost_usd
        )
        return better_quality and better_tokens and better_cost and strictly_better


@dataclass
class RankedIndividual(Generic[T]):
    item: T
    objectives: ObjectiveVector
    rank: int = 0
    crowding: float = 0.0


def fast_non_dominated_sort(individuals: Sequence[RankedIndividual[T]]) -> list[list[RankedIndividual[T]]]:
    """NSGA-II fast non-dominated sorting."""
    fronts: list[list[RankedIndividual[T]]] = [[]]
    domination_count: dict[int, int] = {}
    dominated_by: dict[int, list[int]] = {i: [] for i in range(len(individuals))}

    for i, p in enumerate(individuals):
        domination_count[i] = 0
        for j, q in enumerate(individuals):
            if i == j:
                continue
            if p.objectives.dominates(q.objectives):
                dominated_by[i].append(j)
            elif q.objectives.dominates(p.objectives):
                domination_count[i] += 1
        if domination_count[i] == 0:
            p.rank = 0
            fronts[0].append(p)

    front_index = 0
    while fronts[front_index]:
        next_front: list[RankedIndividual[T]] = []
        for p in fronts[front_index]:
            p_index = individuals.index(p)
            for q_index in dominated_by[p_index]:
                domination_count[q_index] -= 1
                if domination_count[q_index] == 0:
                    individuals[q_index].rank = front_index + 1
                    next_front.append(individuals[q_index])
        front_index += 1
        if next_front:
            fronts.append(next_front)
        else:
            break

    return [front for front in fronts if front]


def crowding_distance(front: list[RankedIndividual[T]]) -> None:
    """Assign crowding distance within a Pareto front."""
    if not front:
        return
    for ind in front:
        ind.crowding = 0.0
    if len(front) <= 2:
        for ind in front:
            ind.crowding = float("inf")
        return

    objectives_list = [
        ("quality", lambda o: o.quality, True),
        ("tokens", lambda o: o.tokens, False),
        ("cost_usd", lambda o: o.cost_usd, False),
    ]

    for _name, accessor, maximize in objectives_list:
        front.sort(key=lambda ind: accessor(ind.objectives))
        front[0].crowding = float("inf")
        front[-1].crowding = float("inf")

        values = [accessor(ind.objectives) for ind in front]
        span = max(values) - min(values)
        if span == 0:
            continue

        for i in range(1, len(front) - 1):
            if front[i].crowding == float("inf"):
                continue
            prev_val = accessor(front[i - 1].objectives)
            next_val = accessor(front[i + 1].objectives)
            front[i].crowding += abs(next_val - prev_val) / span


def nsga2_select(
    individuals: Sequence[RankedIndividual[T]],
    k: int,
) -> list[T]:
    """Select k individuals using NSGA-II rank + crowding distance."""
    if not individuals:
        return []
    if len(individuals) <= k:
        return [ind.item for ind in individuals]

    working = [RankedIndividual(item=ind.item, objectives=ind.objectives) for ind in individuals]
    fronts = fast_non_dominated_sort(working)

    selected: list[RankedIndividual[T]] = []
    for front in fronts:
        crowding_distance(front)
        if len(selected) + len(front) <= k:
            selected.extend(front)
        else:
            front.sort(key=lambda ind: (-ind.crowding if ind.crowding != float("inf") else float("inf")))
            remaining = k - len(selected)
            selected.extend(front[:remaining])
            break

    return [ind.item for ind in selected]


def to_ranked(
    items: Sequence[T],
    objective_fn: Callable[[T], ObjectiveVector],
) -> list[RankedIndividual[T]]:
    return [RankedIndividual(item=item, objectives=objective_fn(item)) for item in items]
