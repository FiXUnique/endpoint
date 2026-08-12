from __future__ import annotations

import sqlite3
from pathlib import Path

from endpoint.models import InvestigationGraph


class InvestigationRepository:
    """Small, durable snapshot store; PostgreSQL can replace it behind this boundary."""

    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_snapshots (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    chain TEXT NOT NULL,
                    seed TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL
                )
                """
            )

    def save(self, graph: InvestigationGraph) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO investigation_snapshots
                    (id, name, chain, seed, created_at, snapshot_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    created_at = excluded.created_at,
                    snapshot_json = excluded.snapshot_json
                """,
                (
                    graph.investigation_id,
                    graph.name,
                    graph.chain,
                    graph.seed,
                    graph.created_at.isoformat(),
                    graph.model_dump_json(),
                ),
            )

    def get(self, investigation_id: str) -> InvestigationGraph | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT snapshot_json FROM investigation_snapshots WHERE id = ?",
                (investigation_id,),
            ).fetchone()
        return InvestigationGraph.model_validate_json(row["snapshot_json"]) if row else None

    def list(self, limit: int = 25) -> list[dict[str, str]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, name, chain, seed, created_at
                FROM investigation_snapshots
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
