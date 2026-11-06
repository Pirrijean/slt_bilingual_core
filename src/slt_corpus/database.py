"""Robust SQLite database layer with WAL mode, foreign keys, and atomic transactions."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class DatabaseError(RuntimeError):
    """Raised when database connection, configuration, or migration fails."""


class CorpusDatabase:
    """Manages SQLite connections, pragmas, schema migrations, and backups."""

    SCHEMA_VERSION = 1

    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        """Create a single isolated connection with mandatory pragmas."""
        connection = sqlite3.connect(
            str(self.path),
            timeout=10.0,
            isolation_level=None,  # Manual autocommit / transaction control
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def initialize(self) -> None:
        """Verify pragmas, execute pending migrations, and assert foreign keys."""
        connection = self._connect()
        try:
            # Enable WAL mode
            mode_row = connection.execute("PRAGMA journal_mode = WAL").fetchone()
            if mode_row is None or str(mode_row[0]).lower() != "wal":
                # In in-memory or some systems, WAL may fallback; verify journal mode
                current_mode = str(connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()
                if current_mode not in ("wal", "memory"):
                    raise DatabaseError(f"SQLite WAL mode could not be enabled: {current_mode}")

            version_row = connection.execute("PRAGMA user_version").fetchone()
            current_version = version_row[0] if version_row else 0

            if current_version > self.SCHEMA_VERSION:
                raise DatabaseError("Database schema is newer than this application.")

            if current_version == 0:
                migration = (
                    Path(__file__).resolve().parents[2]
                    / "schemas"
                    / "sqlite"
                    / "001_initial.sql"
                )
                if not migration.is_file():
                    raise DatabaseError(f"Initial migration not found at: {migration}")

                sql = migration.read_text(encoding="utf-8")
                connection.executescript(sql)

            self._verify_foreign_keys(connection)
        finally:
            connection.close()

    @staticmethod
    def _verify_foreign_keys(connection: sqlite3.Connection) -> None:
        row = connection.execute("PRAGMA foreign_keys").fetchone()
        if row is None or row[0] != 1:
            raise DatabaseError("Foreign key enforcement is disabled.")

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Execute block within an immediate, rollback-safe transaction."""
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @contextmanager
    def read_connection(self) -> Iterator[sqlite3.Connection]:
        """Provide a read-only or query connection."""
        connection = self._connect()
        try:
            yield connection
        finally:
            connection.close()

    def backup(self, destination: str | Path) -> None:
        """Create a consistent live SQLite database backup using Connection.backup()."""
        dst = Path(destination).expanduser().resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        with self.read_connection() as source, sqlite3.connect(str(dst)) as target:
            source.backup(target)

    def integrity_check(self) -> tuple[str, ...]:
        """Run PRAGMA integrity_check and return diagnostic messages."""
        with self.read_connection() as connection:
            rows = connection.execute("PRAGMA integrity_check").fetchall()
            return tuple(str(row[0]) for row in rows)

    def foreign_key_check(self) -> tuple[tuple[str, ...], ...]:
        """Run PRAGMA foreign_key_check and return any violations."""
        with self.read_connection() as connection:
            rows = connection.execute("PRAGMA foreign_key_check").fetchall()
            return tuple(tuple(str(col) for col in row) for row in rows)
