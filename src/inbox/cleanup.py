"""Command-line retention cleanup for Inbox."""

from __future__ import annotations

import os

from .storage import cleanup_expired


def main() -> None:
    """Delete expired unarchived files using environment configuration."""
    database_path = os.environ.get("DATABASE_PATH", "data/inbox.sqlite3")
    storage_dir = os.environ.get("STORAGE_DIR", "data/files")
    retention_days = int(os.environ.get("RETENTION_DAYS", "60"))
    removed = cleanup_expired(database_path, storage_dir, retention_days)
    print(f"removed {removed} expired file(s)")


if __name__ == "__main__":
    main()
