"""SQLite metadata and file lifecycle operations for Inbox."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    stored_name TEXT NOT NULL UNIQUE,
    original_name TEXT NOT NULL,
    suffix TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size INTEGER NOT NULL,
    uploaded_at TEXT NOT NULL,
    archived INTEGER NOT NULL DEFAULT 0
)
"""


def connect(database_path: str | Path) -> sqlite3.Connection:
    """Open a configured SQLite database and return rows as dictionaries."""
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    connection.commit()
    return connection


def add_file(database_path: str | Path, metadata: dict[str, Any]) -> None:
    """Insert one uploaded file's metadata."""
    with connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO files
                (id, stored_name, original_name, suffix, mime_type, size, uploaded_at)
            VALUES (:id, :stored_name, :original_name, :suffix, :mime_type, :size, :uploaded_at)
            """,
            metadata,
        )


def get_file(database_path: str | Path, file_id: str) -> dict[str, Any] | None:
    """Return one file metadata record, or ``None`` when it does not exist."""
    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return dict(row) if row else None


def list_files(
    database_path: str | Path,
    period: str | None = None,
    timezone_name: str = "UTC",
) -> list[dict[str, Any]]:
    """Return file metadata newest first, optionally filtered by local period."""
    query = "SELECT * FROM files"
    parameters: list[str] = []
    if period in {"today", "week", "month"}:
        local_now = datetime.now(ZoneInfo(timezone_name))
        if period == "today":
            local_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            local_start = (local_now - timedelta(days=local_now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            local_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cutoff = local_start.astimezone(UTC).isoformat()
        query += " WHERE uploaded_at >= ?"
        parameters.append(cutoff)
    query += " ORDER BY uploaded_at DESC"
    with connect(database_path) as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def set_archived(database_path: str | Path, file_id: str, archived: bool) -> bool:
    """Set a file's archive state and report whether it existed."""
    with connect(database_path) as connection:
        cursor = connection.execute(
            "UPDATE files SET archived = ? WHERE id = ?",
            (int(archived), file_id),
        )
    return cursor.rowcount == 1


def cleanup_expired(
    database_path: str | Path,
    storage_dir: str | Path,
    age_days: int = 60,
    now: datetime | None = None,
) -> int:
    """Delete unarchived files older than ``age_days`` and return a count."""
    current = now or datetime.now(UTC)
    cutoff = current - timedelta(days=age_days)
    storage = Path(storage_dir)
    with connect(database_path) as connection:
        rows = connection.execute(
            "SELECT id, stored_name FROM files WHERE archived = 0 AND uploaded_at < ?",
            (cutoff.isoformat(),),
        ).fetchall()
        removed = 0
        for row in rows:
            path = storage / row["stored_name"]
            if path.exists():
                path.unlink()
            connection.execute("DELETE FROM files WHERE id = ?", (row["id"],))
            removed += 1
    return removed
