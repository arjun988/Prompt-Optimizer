from openprompt.core.evaluator.semantic import semantic_similarity


def test_semantic_identical() -> None:
    assert semantic_similarity("hello world", "hello world") >= 0.99


def test_semantic_related() -> None:
    score = semantic_similarity(
        "The model improved accuracy significantly",
        "Accuracy improved a lot in the model",
    )
    assert score > 0.2


def test_semantic_unrelated() -> None:
    score = semantic_similarity("quantum physics", "chocolate cake recipe")
    assert score < 0.5
