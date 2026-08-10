"""Google Gemini provider."""

from __future__ import annotations

import os
import time
from typing import Any

from openprompt.providers.base import Message, ModelResponse


class GeminiProvider:
    """
    Google Gemini generateContent API.

    Set ``GOOGLE_API_KEY`` or ``GEMINI_API_KEY``, or pass ``api_key`` explicitly.
    """

    name = "gemini"

    def __init__(
        self,
        model: str = "gemini-2.0-flash",
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.api_key = (
            api_key
            or os.environ.get("GOOGLE_API_KEY")
            or os.environ.get("GEMINI_API_KEY")
        )
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Set GOOGLE_API_KEY or GEMINI_API_KEY, or pass api_key."
            )

    def generate(self, messages: list[Message], **kwargs: Any) -> ModelResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ImportError(
                "Install the Gemini SDK: pip install 'openprompt[gemini]'"
            ) from exc

        client = genai.Client(api_key=self.api_key)
        system_instruction, contents = _to_gemini_contents(messages)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 4096),
        )

        start = time.perf_counter()
        response = client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )
        latency_ms = (time.perf_counter() - start) * 1000

        text = response.text or ""
        usage = response.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0) or 0
        output_tokens = getattr(usage, "candidates_token_count", 0) or 0

        return ModelResponse(
            content=text,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            raw={"provider": "gemini"},
        )


def _to_gemini_contents(messages: list[Message]) -> tuple[str | None, list]:
    from google.genai import types

    system_parts: list[str] = []
    contents: list[types.Content] = []

    for message in messages:
        if message.role == "system":
            system_parts.append(message.content)
            continue

        role = "model" if message.role == "assistant" else "user"
        parts: list = []
        if message.content.strip():
            parts.append(types.Part(text=message.content))
        for media in message.media:
            if media.base64_data:
                import base64

                raw = base64.standard_b64decode(media.base64_data)
                parts.append(
                    types.Part(
                        inline_data=types.Blob(mime_type=media.mime_type, data=raw),
                    )
                )
            elif media.path:
                from pathlib import Path

                raw = Path(media.path).read_bytes()
                parts.append(
                    types.Part(
                        inline_data=types.Blob(mime_type=media.mime_type, data=raw),
                    )
                )
        if not parts:
            parts = [types.Part(text="")]
        contents.append(types.Content(role=role, parts=parts))

    system_instruction = "\n\n".join(system_parts) if system_parts else None

    if not contents:
        contents = [types.Content(role="user", parts=[types.Part(text="")])]

    return system_instruction, contents
