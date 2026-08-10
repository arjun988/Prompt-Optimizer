"""Improve output format and structure."""

from __future__ import annotations

from openprompt.core.ast.models import OutputFormat, OutputSpec, PromptAST
from openprompt.strategies.mutations.base import OptimizeContext

SECTIONS_BY_TASK = {
    "code_review": [
        "Summary",
        "Issues (with severity: Critical/High/Medium/Low)",
        "Recommended fixes",
    ],
    "summarization": ["Key points", "Main argument", "Conclusions", "Actionable insights"],
    "classification": ["Label", "Confidence", "Rationale"],
    "extraction": ["Extracted fields", "Confidence", "Notes"],
    "analysis": ["Key findings", "Anomalies", "Trends", "Recommendations", "Confidence"],
}


class OutputMutation:
    name = "output"

    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST:
        updated = ast.clone()
        task = updated.objective.task if updated.objective else None

        if "json" in str(updated.raw_text or "").lower() or any(
            f in (context.failures or []) for f in ["json", "JSON"]
        ):
            updated.output = OutputSpec(
                format=OutputFormat.JSON,
                schema={"type": "object", "required": ["result"]},
                sections=updated.output.sections if updated.output else [],
            )
            return updated

        sections = SECTIONS_BY_TASK.get(task or "", ["Response"])
        fmt = OutputFormat.MARKDOWN if len(sections) > 1 else OutputFormat.TEXT

        updated.output = OutputSpec(
            format=fmt,
            sections=sections,
            schema_=updated.output.schema_ if updated.output else None,
        )
        return updated
