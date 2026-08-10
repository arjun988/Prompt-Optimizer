"""Phase 5 — RAG, agent, GRPO, few-shot, dataset extraction, multimodal."""

from __future__ import annotations

from pathlib import Path

import yaml

from openprompt.core.ast.models import AgentSpec, OutputFormat, OutputSpec, PromptAST, RAGSpec, ToolSpec
from openprompt.core.compiler.renderer import render_generic, render_messages
from openprompt.core.dataset.models import dataset_to_test_cases, load_dataset
from openprompt.core.media.loader import load_media
from openprompt.core.optimizer.bayesian import tune_optimizer
from openprompt.core.optimizer.few_shot import select_few_shot_examples
from openprompt.core.optimizer.strategies import StrategyContext, builtin_strategy_runners
from openprompt.core.parser.parser import parse_text
from openprompt.plugins.discovery import discover_strategies
from openprompt.providers.base import Message
from openprompt.providers.mock import MockProvider
from openprompt.sdk.client import OpenPrompt


def test_phase5_strategies_registered() -> None:
    runners = discover_strategies()
    for name in ("rag", "agent", "grpo", "few_shot", "extraction"):
        assert name in runners


def test_few_shot_selection_diversity() -> None:
    from openprompt.core.ast.models import ExampleSpec

    pool = [
        ExampleSpec(input="Summarize quarterly revenue trends.", output='{"summary":"..."}'),
        ExampleSpec(input="Extract invoice total and vendor name.", output='{"vendor":"A","total":1}'),
        ExampleSpec(input="Classify support ticket urgency.", output='{"urgency":"high"}'),
    ]
    result = select_few_shot_examples(pool, k=2)
    assert len(result.selected) == 2
    assert result.selected[0].input != result.selected[1].input


def test_rag_spec_renders() -> None:
    from openprompt.core.ast.models import ObjectiveSpec

    ast = PromptAST(
        objective=ObjectiveSpec(raw="Answer using retrieved docs."),
        rag=RAGSpec(enabled=True, context_budget_tokens=1500, require_citations=True),
    )
    text = render_generic(ast)
    assert "Retrieval (RAG)" in text
    assert "1500" in text


def test_agent_tools_render() -> None:
    ast = PromptAST(
        agent=AgentSpec(
            system_prompt="You are a research agent.",
            tools=[ToolSpec(name="search", description="Search the web.", parameters_schema={"type": "object"})],
        )
    )
    text = render_generic(ast)
    assert "search" in text


def test_media_pdf_loader(tmp_path: Path) -> None:
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 minimal")
    attachment = load_media(pdf)
    assert attachment.media_type.value == "pdf"
    assert attachment.extracted_text


def test_dataset_manifest(tmp_path: Path) -> None:
    root = tmp_path / "ds"
    (root / "samples").mkdir(parents=True)
    sample = root / "samples" / "doc.txt"
    sample.write_text("Invoice from Acme for $50", encoding="utf-8")
    manifest = {
        "dataset": {
            "name": "test",
            "schema": {"type": "object", "properties": {"vendor": {"type": "string"}}},
            "samples": [{"name": "doc", "media": "samples/doc.txt", "expected": '{"vendor":"Acme"}'}],
        }
    }
    (root / "dataset.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    ds = load_dataset(root / "dataset.yaml")
    tests = dataset_to_test_cases(ds)
    assert len(tests) == 1
    assert "Acme" in tests[0].input or "Invoice" in tests[0].input


def test_extraction_strategy_mock() -> None:
    from openprompt.core.ast.models import ObjectiveSpec

    ast = PromptAST(
        objective=ObjectiveSpec(raw="Extract JSON from documents."),
        output=OutputSpec(format=OutputFormat.JSON),
    )
    ctx = StrategyContext(provider=MockProvider(), tests=None, config=None)
    result = builtin_strategy_runners()["grpo"](ast, ctx)
    assert result.strategy == "grpo"
    assert result.prompt


def test_bayesian_tune() -> None:
    from openprompt.config.models import ProjectConfig

    result = tune_optimizer(ProjectConfig(), n_trials=5, db_path=":memory:")
    assert result.best_params
    assert "eval_budget" in result.best_params


def test_multimodal_message_parts(tmp_path: Path) -> None:
    img = tmp_path / "x.png"
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
        b"\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    from openprompt.core.ast.models import MediaAttachment, MediaType

    ast = PromptAST(
        objective={"raw": "Describe the image."},
        media=[load_media(img, use_vision=True)],
    )
    messages = render_messages(ast)
    assert messages[-1].media or "image" in render_generic(ast).lower() or messages[-1].content


def test_openprompt_extraction_optimize(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.yaml"
    prompt.write_text(
        yaml.safe_dump(
            {
                "prompt": {
                    "objective": {"raw": "Extract vendor and total as JSON."},
                    "output": {"format": "json"},
                }
            }
        ),
        encoding="utf-8",
    )
    client = OpenPrompt(provider="mock", warn_mock=False)
    result = client.optimize(prompt, strategy="grpo")
    assert result.optimized_score >= 0
