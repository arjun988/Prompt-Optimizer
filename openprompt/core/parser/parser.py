"""Parse plain text and YAML prompts into PromptAST."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from openprompt.core.ast.models import (
    ExampleSpec,
    ObjectiveSpec,
    OutputFormat,
    OutputSpec,
    PromptAST,
    PromptMetadata,
    ReasoningSpec,
    RoleSpec,
    SecuritySpec,
    VerificationSpec,
)
from openprompt.core.compiler.renderer import render_generic


SECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "role": re.compile(r"^(?:you are|act as|role\s*:)\s*(.+)$", re.IGNORECASE | re.MULTILINE),
    "constraints": re.compile(r"^constraints?\s*:\s*$", re.IGNORECASE | re.MULTILINE),
    "context": re.compile(r"^context\s*:\s*$", re.IGNORECASE | re.MULTILINE),
    "output": re.compile(r"^(?:output|return|format)\s*:\s*$", re.IGNORECASE | re.MULTILINE),
    "examples": re.compile(r"^examples?\s*:\s*$", re.IGNORECASE | re.MULTILINE),
}


def parse_file(path: Path | str) -> PromptAST:
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()

    if suffix in {".yaml", ".yml"}:
        ast = parse_yaml(content)
        ast.metadata.source_file = str(path)
        return ast

    ast = parse_text(content)
    ast.metadata.source_file = str(path)
    return ast


def parse_yaml(content: str) -> PromptAST:
    data = yaml.safe_load(content)
    if not data:
        return PromptAST(raw_text=content.strip())

    if "prompt" in data:
        prompt_data = data["prompt"]
    else:
        prompt_data = data

    if isinstance(prompt_data, str):
        return parse_text(prompt_data)

    return _dict_to_ast(prompt_data, raw_text=content.strip())


def parse_text(content: str) -> PromptAST:
    text = content.strip()
    if not text:
        return PromptAST(raw_text="")

    ast = PromptAST(raw_text=text)

    role_match = SECTION_PATTERNS["role"].search(text)
    if role_match:
        ast.role = RoleSpec(description=role_match.group(1).strip().rstrip("."))

    objective = _extract_objective(text)
    if objective:
        ast.objective = objective

    ast.context = _extract_bullet_section(text, "context")
    ast.constraints = _extract_bullet_section(text, "constraints")
    ast.output = _extract_output_section(text)
    ast.examples = _extract_examples(text)

    if re.search(r"\bjson\b", text, re.IGNORECASE) and not ast.output:
        ast.output = OutputSpec(format=OutputFormat.JSON)

    if re.search(r"step by step|verify|double-check", text, re.IGNORECASE):
        ast.reasoning = ReasoningSpec(verify=True)

    if re.search(r"untrusted|injection|do not follow instructions", text, re.IGNORECASE):
        ast.security = SecuritySpec(untrusted_input_isolation=True, treat_context_as_data=True)

    return ast


def parse_any(content: str, *, source_file: str | None = None) -> PromptAST:
    """Auto-detect YAML vs plain text."""
    stripped = content.strip()
    if stripped.startswith("{") or stripped.startswith("prompt:"):
        try:
            ast = parse_yaml(content)
        except yaml.YAMLError:
            ast = parse_text(content)
    else:
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict):
                ast = parse_yaml(content)
            else:
                ast = parse_text(content)
        except yaml.YAMLError:
            ast = parse_text(content)

    if source_file:
        ast.metadata.source_file = source_file
    return ast


def ast_to_text(ast: PromptAST) -> str:
    return render_generic(ast)


def _dict_to_ast(data: dict[str, Any], *, raw_text: str | None = None) -> PromptAST:
    metadata = data.get("metadata", {})
    return PromptAST(
        schema_version=data.get("schema_version", "1.0"),
        metadata=PromptMetadata.model_validate(metadata) if metadata else PromptMetadata(),
        role=RoleSpec.model_validate(data["role"]) if data.get("role") else None,
        objective=ObjectiveSpec.model_validate(data["objective"]) if data.get("objective") else None,
        context=data.get("context", []),
        constraints=data.get("constraints", []),
        examples=[ExampleSpec.model_validate(e) for e in data.get("examples", [])],
        output=OutputSpec.model_validate(data["output"]) if data.get("output") else None,
        verification=VerificationSpec.model_validate(data["verification"])
        if data.get("verification")
        else None,
        reasoning=ReasoningSpec.model_validate(data["reasoning"]) if data.get("reasoning") else None,
        security=SecuritySpec.model_validate(data["security"]) if data.get("security") else None,
        raw_text=raw_text,
    )


def _extract_objective(text: str) -> ObjectiveSpec | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    first = lines[0]
    if SECTION_PATTERNS["role"].match(first):
        if len(lines) > 1:
            return ObjectiveSpec(raw=lines[1])
        return None

    task_keywords = {
        "analyze": "analysis",
        "review": "code_review",
        "summarize": "summarization",
        "classify": "classification",
        "extract": "extraction",
        "fix": "debugging",
        "explain": "explanation",
    }
    lower = first.lower()
    for keyword, task in task_keywords.items():
        if keyword in lower:
            return ObjectiveSpec(task=task, raw=first)

    return ObjectiveSpec(raw=first)


def _extract_bullet_section(text: str, section: str) -> list[str]:
    pattern = SECTION_PATTERNS.get(section)
    if not pattern:
        return []

    match = pattern.search(text)
    if not match:
        return []

    rest = text[match.end() :]
    items: list[str] = []
    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            if items:
                break
            continue
        if re.match(r"^[A-Za-z]+\s*:\s*$", stripped):
            break
        if stripped.startswith(("-", "*", "•")):
            items.append(stripped.lstrip("-*• ").strip())
        elif items:
            break
    return items


def _extract_output_section(text: str) -> OutputSpec | None:
    match = SECTION_PATTERNS["output"].search(text)
    if not match:
        return None

    rest = text[match.end() :]
    sections: list[str] = []
    fmt = OutputFormat.TEXT

    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            if sections:
                break
            continue
        if re.match(r"^[A-Za-z]+\s*:\s*$", stripped) and sections:
            break
        lower = stripped.lower()
        if "json" in lower:
            fmt = OutputFormat.JSON
        elif "markdown" in lower:
            fmt = OutputFormat.MARKDOWN
        if stripped.startswith(("-", "*", "•", "#")):
            sections.append(stripped.lstrip("-*•# ").strip())
        elif sections:
            break

    return OutputSpec(format=fmt, sections=sections) if sections or fmt != OutputFormat.TEXT else OutputSpec(format=fmt)


def _extract_examples(text: str) -> list[ExampleSpec]:
    match = SECTION_PATTERNS["examples"].search(text)
    if not match:
        return []

    rest = text[match.end() :]
    examples: list[ExampleSpec] = []
    current_input: str | None = None

    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if re.match(r"^[A-Za-z]+\s*:\s*$", stripped) and not stripped.lower().startswith(("input", "output")):
            break
        lower = stripped.lower()
        if lower.startswith("input:"):
            current_input = stripped[6:].strip()
        elif lower.startswith("output:") and current_input is not None:
            examples.append(ExampleSpec(input=current_input, output=stripped[7:].strip()))
            current_input = None

    return examples
