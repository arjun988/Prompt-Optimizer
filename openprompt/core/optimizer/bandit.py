"""LinUCB contextual bandit for mutation operator selection."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from openprompt.strategies.mutations.base import MutationOperator


@dataclass
class LinUCBBandit:
    """Simple LinUCB bandit for selecting mutation operators."""

    operators: list[MutationOperator]
    alpha: float = 1.0
    dim: int = 8
    _a: dict[str, list[list[float]]] = field(default_factory=dict, init=False, repr=False)
    _b: dict[str, list[float]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        for op in self.operators:
            self._a[op.name] = _identity(self.dim)
            self._b[op.name] = [0.0] * self.dim

    def select(self, context: list[float], *, explore: float = 0.1) -> MutationOperator:
        if random.random() < explore:
            return random.choice(self.operators)

        if len(context) < self.dim:
            context = context + [0.0] * (self.dim - len(context))
        else:
            context = context[: self.dim]

        best_op = self.operators[0]
        best_score = -math.inf

        for op in self.operators:
            a_inv = _mat_inv(self._a[op.name])
            theta = _mat_vec(a_inv, self._b[op.name])
            mean = _dot(theta, context)
            uncertainty = math.sqrt(max(0.0, _quadratic_form(a_inv, context)))
            ucb = mean + self.alpha * uncertainty
            if ucb > best_score:
                best_score = ucb
                best_op = op

        return best_op

    def update(self, operator_name: str, context: list[float], reward: float) -> None:
        if operator_name not in self._a:
            return
        if len(context) < self.dim:
            context = context + [0.0] * (self.dim - len(context))
        else:
            context = context[: self.dim]

        self._a[operator_name] = _mat_add_outer(self._a[operator_name], context)
        self._b[operator_name] = [b + reward * x for b, x in zip(self._b[operator_name], context)]


def build_context_features(lint_score: int, failure_codes: list[str], token_count: int) -> list[float]:
    """Build a simple feature vector for bandit state."""
    codes = set(failure_codes)
    return [
        lint_score / 100.0,
        1.0 if "missing_output_format" in codes else 0.0,
        1.0 if "missing_json_schema" in codes else 0.0,
        1.0 if "missing_context" in codes else 0.0,
        1.0 if "conflicting_instructions" in codes else 0.0,
        min(1.0, token_count / 4000.0),
        1.0 if "json" in " ".join(failure_codes).lower() else 0.0,
        1.0 if "security" in " ".join(failure_codes).lower() else 0.0,
    ]


def _identity(n: int) -> list[list[float]]:
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _mat_vec(m: list[list[float]], v: list[float]) -> list[float]:
    return [_dot(row, v) for row in m]


def _mat_add_outer(m: list[list[float]], v: list[float]) -> list[list[float]]:
    return [[m[i][j] + v[i] * v[j] for j in range(len(v))] for i in range(len(v))]


def _quadratic_form(m: list[list[float]], v: list[float]) -> float:
    mv = _mat_vec(m, v)
    return _dot(v, mv)


def _mat_inv(m: list[list[float]]) -> list[list[float]]:
    """Gauss-Jordan inversion for small matrices."""
    n = len(m)
    aug = [row[:] + _identity(n)[i] for i, row in enumerate(m)]

    for col in range(n):
        pivot = col
        for row in range(col + 1, n):
            if abs(aug[row][col]) > abs(aug[pivot][col]):
                pivot = row
        aug[col], aug[pivot] = aug[pivot], aug[col]

        pivot_val = aug[col][col]
        if abs(pivot_val) < 1e-12:
            continue
        aug[col] = [v / pivot_val for v in aug[col]]

        for row in range(n):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [aug[row][j] - factor * aug[col][j] for j in range(2 * n)]

    return [row[n:] for row in aug]
