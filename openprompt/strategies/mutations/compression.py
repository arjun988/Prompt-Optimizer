"""Compress prompt while preserving structure."""

from __future__ import annotations

import re

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import render_generic
from openprompt.strategies.mutations.base import OptimizeContext


class CompressionMutation:
    name = "compression"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()

        # Merge redundant constraints
        seen: set[str] = set()
        deduped: list[str] = []
        for constraint in updated.constraints:
            key = constraint.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped.append(constraint)
        updated.constraints = deduped

        # Trim verbose role
        if updated.role and updated.role.description:
            desc = updated.role.description
            desc = re.sub(r"\s+", " ", desc).strip()
            updated.role.description = desc

        # Drop duplicate context lines
        ctx_seen: set[str] = set()
        unique_context: list[str] = []
        for item in updated.context:
            key = item.lower().strip()
            if key not in ctx_seen:
                ctx_seen.add(key)
                unique_context.append(item)
        updated.context = unique_context

        # If still very long, collapse raw text into objective
        text = render_generic(updated)
        if len(text) > 2000 and updated.raw_text:
            if not updated.objective:
                from openprompt.core.ast.models import ObjectiveSpec

                updated.objective = ObjectiveSpec(raw=updated.raw_text[:500])
            updated.raw_text = None

        return updated
