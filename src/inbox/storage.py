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
    """Open a SQLite database and configure dictionary-like result rows.

    Args:
        database_path: Path to the SQLite database file. Parent directories are
            expected to exist or be created by the caller.

    Returns:
        An open SQLite connection with the Inbox schema initialized and rows
        configured as ``sqlite3.Row`` objects.

    Examples:
        >>> connection = connect("data/inbox.sqlite3")
        >>> connection.row_factory is sqlite3.Row
        True
        >>> connection.close()
    """
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute(SCHEMA)
    connection.commit()
    return connection


def add_file(database_path: str | Path, metadata: dict[str, Any]) -> None:
    """Store metadata for one uploaded file.

    Args:
        database_path: Path to the SQLite database file.
        metadata: Mapping containing the ``files`` table fields ``id``,
            ``stored_name``, ``original_name``, ``suffix``, ``mime_type``,
            ``size``, and ``uploaded_at``.

    Raises:
        sqlite3.IntegrityError: If the file ID or stored name already exists,
            or a required metadata field is missing.

    Examples:
        >>> add_file("data/inbox.sqlite3", {
        ...     "id": "abc123", "stored_name": "2026-note.txt",
        ...     "original_name": "note.txt", "suffix": "note",
        ...     "mime_type": "text/plain", "size": 4,
        ...     "uploaded_at": "2026-01-01T12:00:00+00:00",
        ... })
    """
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
    """Retrieve one file metadata record by its opaque ID.

    Args:
        database_path: Path to the SQLite database file.
        file_id: Stable opaque identifier assigned when the file was uploaded.

    Returns:
        A dictionary containing the stored metadata, or ``None`` when no record
        has the requested ID.

    Examples:
        >>> get_file("data/inbox.sqlite3", "missing") is None
        True
    """
    with connect(database_path) as connection:
        row = connection.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    return dict(row) if row else None


def list_files(
    database_path: str | Path,
    period: str | None = None,
    timezone_name: str = "UTC",
) -> list[dict[str, Any]]:
    """List file metadata, optionally filtered by a local calendar period.

    Args:
        database_path: Path to the SQLite database file.
        period: Optional filter: ``"today"``, ``"week"``, or ``"month"``.
            Unknown values are treated as no filter.
        timezone_name: IANA timezone used to determine the period boundary.

    Returns:
        File metadata dictionaries sorted newest first. Each dictionary has the
        columns returned by the ``files`` table.

    Raises:
        zoneinfo.ZoneInfoNotFoundError: If ``timezone_name`` is not a known IANA
            timezone.

    Examples:
        >>> rows = list_files("data/inbox.sqlite3", period="today")
        >>> isinstance(rows, list)
        True
    """
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
    """Set a file's archive state.

    Args:
        database_path: Path to the SQLite database file.
        file_id: Stable opaque identifier assigned when the file was uploaded.
        archived: ``True`` to preserve the file during cleanup; ``False`` to
            make it eligible for retention cleanup.

    Returns:
        ``True`` when a record was updated, otherwise ``False``.

    Examples:
        >>> set_archived("data/inbox.sqlite3", "missing", True)
        False
    """
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
    """Remove expired unarchived files and return the number removed.

    Args:
        database_path: Path to the SQLite database file.
        storage_dir: Directory containing the stored file payloads.
        age_days: Age threshold in days. Files uploaded before the calculated
            cutoff are eligible for removal.
        now: Optional timezone-aware UTC timestamp used as the current time.
            Supplying it makes cleanup deterministic in tests and maintenance
            jobs.

    Returns:
        Number of metadata records removed. Missing payloads are tolerated and
        their metadata is still removed.

    Examples:
        >>> cleanup_expired("data/inbox.sqlite3", "data/files", age_days=60)
        0
    """
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
