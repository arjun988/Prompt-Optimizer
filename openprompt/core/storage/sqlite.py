"""Local SQLite observability storage."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RunRecord:
    id: int | None
    prompt_name: str
    strategy: str
    model: str
    score: float
    tokens: int
    cost_usd: float
    latency_ms: float
    created_at: str


class RunStore:
    """Persist optimization and evaluation runs locally."""

    def __init__(self, db_path: str | Path = ".openprompt/runs.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_name TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    model TEXT NOT NULL,
                    score REAL NOT NULL,
                    tokens INTEGER NOT NULL,
                    cost_usd REAL DEFAULT 0,
                    latency_ms REAL DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def log_run(
        self,
        *,
        prompt_name: str,
        strategy: str,
        model: str,
        score: float,
        tokens: int,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        metadata: dict | None = None,
    ) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO runs (prompt_name, strategy, model, score, tokens, cost_usd, latency_ms, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    prompt_name,
                    strategy,
                    model,
                    score,
                    tokens,
                    cost_usd,
                    latency_ms,
                    json.dumps(metadata or {}),
                    created_at,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def recent_runs(self, limit: int = 20) -> list[RunRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            RunRecord(
                id=row["id"],
                prompt_name=row["prompt_name"],
                strategy=row["strategy"],
                model=row["model"],
                score=row["score"],
                tokens=row["tokens"],
                cost_usd=row["cost_usd"],
                latency_ms=row["latency_ms"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def average_score(self, prompt_name: str) -> float | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT AVG(score) AS avg_score FROM runs WHERE prompt_name = ?",
                (prompt_name,),
            ).fetchone()
        if row and row["avg_score"] is not None:
            return float(row["avg_score"])
        return None
