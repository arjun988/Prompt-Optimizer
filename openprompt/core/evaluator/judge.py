"""LLM-as-judge evaluation."""

from __future__ import annotations

import json
import re
from typing import Any

from openprompt.providers.base import Message, ModelProvider

DEFAULT_RUBRIC = """Score the model response from 0.0 to 1.0 on:
- correctness (factual accuracy)
- relevance (addresses the input)
- instruction_following (meets format/requirements)
- hallucination (penalize unsupported claims)

Return JSON only: {"score": <float>, "reason": "<brief explanation>"}"""


def judge_response(
    provider: ModelProvider,
    input_text: str,
    output: str,
    expected: str | None = None,
    metadata: dict[str, Any] | None = None,
    rubric: str | None = None,
) -> tuple[float, str]:
    """Use an LLM to score a response."""
    meta = metadata or {}
    rubric_text = rubric or meta.get("rubric") or DEFAULT_RUBRIC

    prompt_parts = [
        rubric_text,
        "",
        f"User input:\n{input_text}",
        "",
        f"Model response:\n{output}",
    ]
    if expected:
        prompt_parts.extend(["", f"Reference expected output:\n{expected}"])

    messages = [Message(role="user", content="\n".join(prompt_parts))]
    response = provider.generate(messages, temperature=0.0)

    return _parse_judge_response(response.content)


def _parse_judge_response(content: str) -> tuple[float, str]:
    content = content.strip()

    try:
        data = json.loads(content)
        score = float(data.get("score", 0))
        reason = str(data.get("reason", ""))
        return max(0.0, min(1.0, score)), reason or "LLM judge score."
    except json.JSONDecodeError:
        pass

    match = re.search(r"score[\"']?\s*[:=]\s*([0-9.]+)", content, re.IGNORECASE)
    if match:
        return max(0.0, min(1.0, float(match.group(1)))), content[:200]

    return 0.5, "Could not parse judge response; defaulting to 0.5."
