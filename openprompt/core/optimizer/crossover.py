"""AST crossover (merge) for evolutionary prompt optimization."""

from __future__ import annotations

from openprompt.core.ast.models import (
    ExampleSpec,
    ObjectiveSpec,
    OutputSpec,
    PromptAST,
    ReasoningSpec,
    RoleSpec,
    SecuritySpec,
    VerificationSpec,
)


def crossover_ast(parent_a: PromptAST, parent_b: PromptAST) -> PromptAST:
    """
    Merge two prompt ASTs into a child.

    Combines constraints, context, examples, and output specs from both parents
    while deduplicating and preserving the strongest structural elements.
    """
    child = parent_a.clone()

    child.role = _merge_role(parent_a.role, parent_b.role)
    child.objective = _merge_objective(parent_a.objective, parent_b.objective)
    child.context = _merge_unique(parent_a.context, parent_b.context)
    child.constraints = _merge_unique(parent_a.constraints, parent_b.constraints)
    child.examples = _merge_examples(parent_a.examples, parent_b.examples)
    child.output = _merge_output(parent_a.output, parent_b.output)
    child.verification = _merge_verification(parent_a.verification, parent_b.verification)
    child.reasoning = _merge_reasoning(parent_a.reasoning, parent_b.reasoning)
    child.security = _merge_security(parent_a.security, parent_b.security)

    if parent_b.raw_text and not _has_rich_structure(child):
        child.raw_text = parent_b.raw_text

    return child


def _merge_role(a: RoleSpec | None, b: RoleSpec | None) -> RoleSpec | None:
    if a and a.enabled and a.description:
        if b and b.enabled and b.description and len(b.description) > len(a.description):
            return b.model_copy(deep=True)
        return a.model_copy(deep=True)
    if b and b.enabled and b.description:
        return b.model_copy(deep=True)
    return a.model_copy(deep=True) if a else None


def _merge_objective(a: ObjectiveSpec | None, b: ObjectiveSpec | None) -> ObjectiveSpec | None:
    if not a and not b:
        return None
    if not a:
        return b.model_copy(deep=True) if b else None
    if not b:
        return a.model_copy(deep=True)

    merged = a.model_copy(deep=True)
    if not merged.task and b.task:
        merged.task = b.task
    if b.description and (not merged.description or len(b.description) > len(merged.description)):
        merged.description = b.description
    if b.raw and (not merged.raw or len(b.raw) > len(merged.raw)):
        merged.raw = b.raw
    return merged


def _merge_unique(a_list: list[str], b_list: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for item in [*a_list, *b_list]:
        key = item.lower().strip()
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged


def _merge_examples(a: list[ExampleSpec], b: list[ExampleSpec]) -> list[ExampleSpec]:
    seen: set[tuple[str, str]] = set()
    merged: list[ExampleSpec] = []
    for ex in [*a, *b]:
        key = (ex.input.strip(), ex.output.strip())
        if key not in seen:
            seen.add(key)
            merged.append(ex.model_copy(deep=True))
    return merged[:6]


def _merge_output(a: OutputSpec | None, b: OutputSpec | None) -> OutputSpec | None:
    if not a and not b:
        return None
    if not a:
        return b.model_copy(deep=True) if b else None
    if not b:
        return a.model_copy(deep=True)

    merged = a.model_copy(deep=True)
    if b.schema_ and not merged.schema_:
        merged.schema_ = b.schema_
    merged.sections = _merge_unique(a.sections, b.sections)
    if b.max_length and (not merged.max_length or b.max_length < merged.max_length):
        merged.max_length = b.max_length
    return merged


def _merge_verification(a: VerificationSpec | None, b: VerificationSpec | None) -> VerificationSpec | None:
    if not a and not b:
        return None
    enabled = bool((a and a.enabled) or (b and b.enabled))
    steps = _merge_unique(
        a.steps if a else [],
        b.steps if b else [],
    )
    return VerificationSpec(enabled=enabled, steps=steps)


def _merge_reasoning(a: ReasoningSpec | None, b: ReasoningSpec | None) -> ReasoningSpec | None:
    if not a and not b:
        return None
    return ReasoningSpec(
        decompose=bool((a and a.decompose) or (b and b.decompose)),
        verify=bool((a and a.verify) or (b and b.verify)),
        critique=bool((a and a.critique) or (b and b.critique)),
        steps=_merge_unique(a.steps if a else [], b.steps if b else []),
    )


def _merge_security(a: SecuritySpec | None, b: SecuritySpec | None) -> SecuritySpec | None:
    if not a and not b:
        return None
    return SecuritySpec(
        untrusted_input_isolation=bool(
            (a and a.untrusted_input_isolation) or (b and b.untrusted_input_isolation)
        ),
        treat_context_as_data=bool(
            (a and a.treat_context_as_data) or (b and b.treat_context_as_data)
        ),
        warnings=_merge_unique(a.warnings if a else [], b.warnings if b else []),
    )


def _has_rich_structure(ast: PromptAST) -> bool:
    return bool(
        ast.role
        or ast.constraints
        or ast.output
        or ast.examples
        or ast.verification
        or ast.reasoning
    )
