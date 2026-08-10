"""Prompt AST schema migration."""

from __future__ import annotations

from typing import Any

from openprompt.core.ast.models import PromptAST


CURRENT_SCHEMA = "1.0"
SUPPORTED = {"1.0"}


def migrate_prompt_data(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate prompt dict to current schema version."""
    if "prompt" in data:
        inner = data["prompt"]
    else:
        inner = data

    version = inner.get("schema_version", "1.0")
    if version not in SUPPORTED:
        inner = _migrate_from_legacy(inner, version)
    inner["schema_version"] = CURRENT_SCHEMA
    return {"prompt": inner} if "prompt" in data else inner


def migrate_ast(ast: PromptAST) -> PromptAST:
    if ast.schema_version in SUPPORTED:
        return ast
    data = ast.model_dump(mode="json")
    migrated = migrate_prompt_data({"prompt": data})["prompt"]
    return PromptAST.model_validate(migrated)


def _migrate_from_legacy(data: dict[str, Any], version: str) -> dict[str, Any]:
    migrated = dict(data)
    if version == "0.9":
        if "instructions" in migrated and "objective" not in migrated:
            migrated["objective"] = {"raw": migrated.pop("instructions")}
    migrated["schema_version"] = CURRENT_SCHEMA
    return migrated
