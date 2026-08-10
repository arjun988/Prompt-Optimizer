"""Pydantic models for the Prompt AST intermediate representation."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class OutputFormat(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    YAML = "yaml"


class RoleSpec(BaseModel):
    """Persona or expertise framing for the model."""

    description: str | None = None
    enabled: bool = True


class ObjectiveSpec(BaseModel):
    """Primary task the prompt asks the model to perform."""

    task: str | None = None
    description: str | None = None
    raw: str | None = None


class OutputSpec(BaseModel):
    """Expected response structure and format."""

    format: OutputFormat | str = OutputFormat.TEXT
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    sections: list[str] = Field(default_factory=list)
    max_length: int | None = None

    model_config = {"populate_by_name": True}


class ExampleSpec(BaseModel):
    """Few-shot demonstration pair."""

    input: str
    output: str
    label: str | None = None


class VerificationSpec(BaseModel):
    """Self-check or verification steps before returning."""

    enabled: bool = False
    steps: list[str] = Field(default_factory=list)


class ReasoningSpec(BaseModel):
    """Structured reasoning strategy (not blind chain-of-thought)."""

    decompose: bool = False
    verify: bool = False
    critique: bool = False
    steps: list[str] = Field(default_factory=list)


class SecuritySpec(BaseModel):
    """Security-related prompt configuration."""

    untrusted_input_isolation: bool = False
    treat_context_as_data: bool = False
    warnings: list[str] = Field(default_factory=list)


class PromptMetadata(BaseModel):
    """Versioning and provenance metadata."""

    name: str | None = None
    version: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_file: str | None = None


class PromptAST(BaseModel):
    """
    Structured intermediate representation of a prompt.

    Prompts flow: text/YAML → PromptAST → optimizer → PromptAST → renderer → provider messages.
    """

    schema_version: str = "1.0"
    metadata: PromptMetadata = Field(default_factory=PromptMetadata)
    role: RoleSpec | None = None
    objective: ObjectiveSpec | None = None
    context: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    examples: list[ExampleSpec] = Field(default_factory=list)
    output: OutputSpec | None = None
    verification: VerificationSpec | None = None
    reasoning: ReasoningSpec | None = None
    security: SecuritySpec | None = None
    raw_text: str | None = None

    def estimate_tokens(self) -> int:
        """Rough token estimate (~4 chars per token)."""
        from openprompt.core.compiler.tokens import estimate_tokens_from_ast

        return estimate_tokens_from_ast(self)

    def clone(self) -> PromptAST:
        return self.model_copy(deep=True)
