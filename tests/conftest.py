"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from openprompt.core.ast.models import ObjectiveSpec, OutputFormat, OutputSpec, PromptAST, RoleSpec
from openprompt.providers.mock import MockProvider


@pytest.fixture
def mock_provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def sample_ast() -> PromptAST:
    return PromptAST(
        role=RoleSpec(description="an expert assistant", enabled=True),
        objective=ObjectiveSpec(task="summarization", raw="Summarize this article."),
        constraints=["Be accurate"],
        output=OutputSpec(format=OutputFormat.MARKDOWN, sections=["Key points"]),
    )


@pytest.fixture
def examples_dir() -> Path:
    return Path(__file__).parent.parent / "examples"


@pytest.fixture
def benchmarks_dir() -> Path:
    return Path(__file__).parent.parent / "benchmarks"
