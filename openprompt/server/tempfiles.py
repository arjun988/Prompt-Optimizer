"""Temporary file helpers with guaranteed cleanup."""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import yaml


@contextmanager
def temp_tests_file(tests: list[dict[str, Any]] | None) -> Iterator[Path | None]:
    if not tests:
        yield None
        return
    fd, name = tempfile.mkstemp(suffix=".yaml", prefix="openprompt_tests_")
    os.close(fd)
    path = Path(name)
    try:
        path.write_text(yaml.safe_dump({"tests": tests}), encoding="utf-8")
        yield path
    finally:
        path.unlink(missing_ok=True)


@contextmanager
def temp_prompt_files(prompts: list[str]) -> Iterator[list[Path]]:
    paths: list[Path] = []
    try:
        for index, text in enumerate(prompts):
            fd, name = tempfile.mkstemp(suffix=f"_{index}.txt", prefix="openprompt_prompt_")
            os.close(fd)
            path = Path(name)
            path.write_text(text, encoding="utf-8")
            paths.append(path)
        yield paths
    finally:
        for path in paths:
            path.unlink(missing_ok=True)
