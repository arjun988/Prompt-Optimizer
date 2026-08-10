from pathlib import Path

from openprompt.core.ast.models import PromptAST, ObjectiveSpec
from openprompt.core.versioning.diff import diff_prompts, diff_versions, save_version, load_version


def test_save_and_diff_versions(tmp_path: Path) -> None:
    a = PromptAST(objective=ObjectiveSpec(raw="Summarize briefly."))
    b = PromptAST(objective=ObjectiveSpec(raw="Summarize in 5 bullet points."), constraints=["Be accurate"])
    save_version(a, tmp_path, "v1")
    save_version(b, tmp_path, "v2")
    loaded = load_version(tmp_path, "v1")
    assert loaded.objective
    diff = diff_versions(tmp_path, "v1", "v2")
    assert diff.added or diff.changed


def test_diff_prompts_detects_constraint_addition() -> None:
    a = PromptAST(constraints=[])
    b = PromptAST(constraints=["No hallucination"])
    diff = diff_prompts(a, b)
    assert any("constraint" in item.lower() for item in diff.added)
