"""Parallel execution helpers."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, TypeVar

T = TypeVar("T")
R = TypeVar("R")


def parallel_map(items: list[T], fn: Callable[[T], R], *, max_workers: int = 4) -> list[R]:
    """Map *fn* over *items* in parallel, preserving input order."""
    if not items:
        return []
    if len(items) == 1:
        return [fn(items[0])]

    results: dict[int, R] = {}
    with ThreadPoolExecutor(max_workers=min(max_workers, len(items))) as pool:
        futures = {pool.submit(fn, item): index for index, item in enumerate(items)}
        for future in as_completed(futures):
            index = futures[future]
            results[index] = future.result()
    return [results[i] for i in range(len(items))]
