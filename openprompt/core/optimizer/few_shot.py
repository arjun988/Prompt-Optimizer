"""Automatic few-shot example selection via embedding diversity and difficulty."""

from __future__ import annotations

import math
from dataclasses import dataclass

from openprompt.core.ast.models import ExampleSpec, PromptAST
from openprompt.core.evaluator.metrics import TestCase, score_output
from openprompt.core.evaluator.semantic import semantic_similarity


@dataclass
class FewShotSelectionResult:
    selected: list[ExampleSpec]
    scores: list[float]
    reason: str


def select_few_shot_examples(
    pool: list[ExampleSpec],
    *,
    k: int = 3,
    task_description: str = "",
    difficulty_tests: list[TestCase] | None = None,
    scorer=None,
) -> FewShotSelectionResult:
    """
    Select *k* diverse, informative examples from a pool.

    Uses embedding diversity (max-min) and optional difficulty from eval failures.
    """
    if not pool:
        return FewShotSelectionResult([], [], "Empty example pool.")
    if len(pool) <= k:
        return FewShotSelectionResult(list(pool), [1.0] * len(pool), "Pool smaller than k.")

    difficulty_map = _score_difficulty(pool, difficulty_tests, scorer)
    selected: list[ExampleSpec] = []
    selected_scores: list[float] = []

    # Seed: hardest example
    ranked = sorted(pool, key=lambda ex: difficulty_map.get(id(ex), 0.5), reverse=True)
    selected.append(ranked[0])
    selected_scores.append(difficulty_map.get(id(ranked[0]), 0.5))

    remaining = [ex for ex in pool if ex is not ranked[0]]
    while len(selected) < k and remaining:
        best: ExampleSpec | None = None
        best_score = -1.0
        for candidate in remaining:
            diversity = min(semantic_similarity(candidate.input, s.input) for s in selected)
            diversity_score = 1.0 - diversity
            difficulty = difficulty_map.get(id(candidate), 0.5)
            combined = 0.6 * diversity_score + 0.4 * difficulty
            if combined > best_score:
                best_score = combined
                best = candidate
        if best is None:
            break
        selected.append(best)
        selected_scores.append(best_score)
        remaining.remove(best)

    return FewShotSelectionResult(
        selected=selected,
        scores=selected_scores,
        reason=f"Selected {len(selected)} examples via diversity + difficulty scoring.",
    )


def apply_few_shot_to_ast(ast: PromptAST, selected: list[ExampleSpec]) -> PromptAST:
    return ast.model_copy(update={"examples": selected})


def _score_difficulty(
    pool: list[ExampleSpec],
    tests: list[TestCase] | None,
    scorer,
) -> dict[int, float]:
    scores: dict[int, float] = {}
    for example in pool:
        if example.difficulty is not None:
            scores[id(example)] = example.difficulty
            continue
        if tests:
            failures = 0
            for test in tests[:5]:
                fake = TestCase(name="probe", input=test.input, expected=example.output, metric=test.metric)
                if scorer:
                    s, _ = scorer(example.output, fake)
                else:
                    s, _ = score_output(example.output, fake)
                if s < 0.85:
                    failures += 1
            scores[id(example)] = failures / max(1, min(5, len(tests)))
        else:
            scores[id(example)] = 0.5 + 0.1 * min(5, len(example.input.split()) / 20)
    return scores
