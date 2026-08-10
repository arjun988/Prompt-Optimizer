from openprompt.core.optimizer.pareto import ObjectiveVector, RankedIndividual, nsga2_select, to_ranked


def test_pareto_dominance() -> None:
    a = ObjectiveVector(quality=0.9, tokens=100, cost_usd=0.01)
    b = ObjectiveVector(quality=0.8, tokens=200, cost_usd=0.02)
    assert a.dominates(b)


def test_nsga2_select_prefers_quality() -> None:
    items = [
        RankedIndividual("low", ObjectiveVector(0.5, 200, 0.02)),
        RankedIndividual("high", ObjectiveVector(0.9, 100, 0.01)),
        RankedIndividual("mid", ObjectiveVector(0.7, 300, 0.03)),
    ]
    selected = nsga2_select(items, 2)
    labels = {s for s in selected}
    assert "high" in labels


def test_to_ranked_wrapper() -> None:
    data = ["a", "b"]
    ranked = to_ranked(data, lambda x: ObjectiveVector(0.5 if x == "a" else 0.8, 10, 0.0))
    assert len(ranked) == 2
