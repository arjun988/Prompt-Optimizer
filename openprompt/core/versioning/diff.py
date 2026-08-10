"""Prompt versioning and diff utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from openprompt.core.ast.models import PromptAST
from openprompt.core.compiler.renderer import ast_to_yaml_dict, render_generic
from openprompt.core.parser.parser import parse_file


@dataclass
class PromptDiff:
    added: list[str]
    removed: list[str]
    changed: list[str]

    def to_text(self) -> str:
        lines: list[str] = []
        for item in self.added:
            lines.append(f"+ {item}")
        for item in self.removed:
            lines.append(f"- {item}")
        for item in self.changed:
            lines.append(f"~ {item}")
        return "\n".join(lines) if lines else "No structural differences."


def save_version(ast: PromptAST, directory: Path, version: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{version}.yaml"
    data = ast_to_yaml_dict(ast)
    if ast.metadata.name:
        data["prompt"]["metadata"]["name"] = ast.metadata.name
    data["prompt"]["metadata"]["version"] = version
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def load_version(directory: Path, version: str) -> PromptAST:
    path = _version_path(directory, version)
    if not path.exists():
        raise FileNotFoundError(f"Version not found: {path}")
    return parse_file(path)


def diff_versions(directory: Path, version_a: str, version_b: str) -> PromptDiff:
    """Diff two version labels within a version directory."""
    return diff_prompts(load_version(directory, version_a), load_version(directory, version_b))


def _version_path(directory: Path, version: str) -> Path:
    label = version if version.endswith((".yaml", ".yml")) else f"{version}.yaml"
    return directory / label


def diff_prompts(a: PromptAST, b: PromptAST) -> PromptDiff:
    added: list[str] = []
    removed: list[str] = []
    changed: list[str] = []

    def _list_diff(label: str, old: list[str], new: list[str]) -> None:
        old_set, new_set = set(old), set(new)
        for item in new_set - old_set:
            added.append(f"{label}: {item}")
        for item in old_set - new_set:
            removed.append(f"{label}: {item}")

    _list_diff("constraint", a.constraints, b.constraints)
    _list_diff("context", a.context, b.context)

    if (a.role and a.role.description) != (b.role and b.role.description):
        if b.role and b.role.description and not (a.role and a.role.description):
            added.append(f"role: {b.role.description}")
        elif a.role and a.role.description and not (b.role and b.role.description):
            removed.append(f"role: {a.role.description}")
        else:
            changed.append(f"role: '{a.role.description if a.role else ''}' → '{b.role.description if b.role else ''}'")

    fmt_a = a.output.format if a.output else None
    fmt_b = b.output.format if b.output else None
    if fmt_a != fmt_b:
        changed.append(f"output format: {fmt_a} → {fmt_b}")

    if a.output and b.output:
        _list_diff("output section", a.output.sections, b.output.sections)

    text_a = render_generic(a)
    text_b = render_generic(b)
    if len(text_b) != len(text_a):
        delta_pct = (len(text_b) - len(text_a)) / max(len(text_a), 1) * 100
        changed.append(f"text length: {len(text_a)} → {len(text_b)} ({delta_pct:+.1f}%)")

    return PromptDiff(added=added, removed=removed, changed=changed)


def diff_files(path_a: Path, path_b: Path) -> PromptDiff:
    return diff_prompts(parse_file(path_a), parse_file(path_b))
