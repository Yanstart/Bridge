"""FallbackQueue : file de repli SQLite WAL pour les Bundles FHIR non livres.

Schema minimal :

    CREATE TABLE fallback_queue (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id    TEXT    NOT NULL,
        payload      TEXT    NOT NULL,
        enqueued_at  TEXT    NOT NULL,  -- ISO 8601 UTC
        retries      INTEGER DEFAULT 0,
        last_error   TEXT
    );

Le mode WAL est active pour autoriser des ecritures concurrentes
non-bloquantes. La queue est purgee au succes du rejeu.

Aucune valeur clinique patient n'est journalisee : seul le payload FHIR
serialise est stocke, et il quitte la table des qu'il est livre.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

import structlog

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class QueueItem:
    id: int
    device_id: str
    payload: dict[str, Any]
    enqueued_at: datetime
    retries: int
    last_error: str | None


class FallbackQueue:
    """File de repli persistante."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.db_path), isolation_level=None)
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fallback_queue (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id    TEXT    NOT NULL,
                    payload      TEXT    NOT NULL,
                    enqueued_at  TEXT    NOT NULL,
                    retries      INTEGER DEFAULT 0,
                    last_error   TEXT
                );
                """
            )

    def enqueue(self, device_id: str, payload: dict[str, Any], error: str | None = None) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO fallback_queue (device_id, payload, enqueued_at, retries, last_error)
                VALUES (?, ?, ?, ?, ?);
                """,
                (
                    device_id,
                    json.dumps(payload),
                    datetime.now(tz=UTC).isoformat(),
                    0,
                    error,
                ),
            )
            new_id = cur.lastrowid
        logger.info("fallback_queue.enqueued", device_id=device_id, item_id=new_id)
        return int(new_id) if new_id is not None else -1

    def list_pending(self, limit: int = 50) -> list[QueueItem]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT id, device_id, payload, enqueued_at, retries, last_error
                FROM fallback_queue
                ORDER BY id ASC
                LIMIT ?;
                """,
                (limit,),
            )
            rows = cur.fetchall()
        return [
            QueueItem(
                id=row[0],
                device_id=row[1],
                payload=json.loads(row[2]),
                enqueued_at=datetime.fromisoformat(row[3]),
                retries=row[4],
                last_error=row[5],
            )
            for row in rows
        ]

    def mark_sent(self, item_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM fallback_queue WHERE id = ?;", (item_id,))
        logger.info("fallback_queue.sent", item_id=item_id)

    def mark_failed(self, item_id: int, error: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE fallback_queue
                SET retries = retries + 1, last_error = ?
                WHERE id = ?;
                """,
                (error, item_id),
            )

    def count(self) -> int:
        with self._connect() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM fallback_queue;")
            row = cur.fetchone()
        return int(row[0]) if row else 0
