"""Read-only preservation audit for Hermes' canonical SessionDB."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


REQUIRED_TABLES = frozenset({"schema_version", "sessions", "messages"})


@dataclass(frozen=True)
class SessionDbHealth:
    healthy: bool
    status: str
    state_db_path: str
    schema_version: int | None = None
    session_count: int | None = None
    message_count: int | None = None
    orphan_message_count: int | None = None
    journal_mode: str | None = None
    database_bytes: int | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _report(
    healthy: bool,
    status: str,
    database: Path,
    **values: Any,
) -> SessionDbHealth:
    size = None
    try:
        if database.is_file():
            size = database.stat().st_size
    except OSError:
        pass
    return SessionDbHealth(
        healthy,
        status,
        str(database),
        database_bytes=size,
        **values,
    )


def probe_sessiondb(_ctx) -> SessionDbHealth:
    """Audit canonical profile history without opening a Hermes writer or migrating schema."""
    database = get_hermes_home().resolve() / "state.db"
    if database.is_symlink() or not database.is_file():
        return _report(False, "storage_missing", database)

    try:
        uri = f"file:{database.as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1.0) as connection:
            connection.execute("PRAGMA query_only=ON")
            journal_row = connection.execute("PRAGMA journal_mode").fetchone()
            journal_mode = str(journal_row[0]).lower() if journal_row else None
            integrity = connection.execute("PRAGMA quick_check").fetchone()
            if not integrity or integrity[0] != "ok":
                return _report(
                    False,
                    "integrity_error",
                    database,
                    journal_mode=journal_mode,
                )
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if not REQUIRED_TABLES.issubset(tables):
                return _report(
                    False,
                    "schema_error",
                    database,
                    journal_mode=journal_mode,
                )
            version_row = connection.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            if (
                not version_row
                or isinstance(version_row[0], bool)
                or not isinstance(version_row[0], int)
                or version_row[0] < 1
            ):
                return _report(
                    False,
                    "schema_error",
                    database,
                    journal_mode=journal_mode,
                )
            foreign_key_error = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchone()
            session_count = int(
                connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            )
            message_count = int(
                connection.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            )
            orphan_message_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM messages m "
                    "LEFT JOIN sessions s ON s.id = m.session_id "
                    "WHERE s.id IS NULL"
                ).fetchone()[0]
            )
            if foreign_key_error or orphan_message_count:
                return _report(
                    False,
                    "referential_integrity_error",
                    database,
                    schema_version=version_row[0],
                    session_count=session_count,
                    message_count=message_count,
                    orphan_message_count=orphan_message_count,
                    journal_mode=journal_mode,
                )
        return _report(
            True,
            "healthy",
            database,
            schema_version=version_row[0],
            session_count=session_count,
            message_count=message_count,
            orphan_message_count=orphan_message_count,
            journal_mode=journal_mode,
        )
    except Exception as exc:
        return _report(
            False,
            "storage_error",
            database,
            error_type=type(exc).__name__,
        )
