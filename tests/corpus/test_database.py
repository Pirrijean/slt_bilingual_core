"""Unit tests for slt_corpus.database SQLite engine and transactions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from slt_corpus.database import CorpusDatabase


def test_database_initialization_and_pragmas(tmp_path: Path):
    db_file = tmp_path / "test.db"
    db = CorpusDatabase(db_file)

    with db.read_connection() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        assert journal_mode.lower() == "wal"
        foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        assert foreign_keys == 1

        # Check initial schema user_version was applied
        ver = conn.execute("PRAGMA user_version;").fetchone()[0]
        assert ver == 1

        # Check participants table exists from 001_initial.sql
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='participants';"
        ).fetchone()
        assert table_exists is not None


def test_database_transaction_commit_and_rollback(tmp_path: Path):
    db_file = tmp_path / "test_tx.db"
    db = CorpusDatabase(db_file)

    # Insert valid participant
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO participants (signer_id, metadata_schema_version, created_at_utc) "
            "VALUES ('signer_tx', '1.0.0', '2026-11-06T10:00:00Z');"
        )

    # Verify committed
    with db.read_connection() as conn:
        row = conn.execute("SELECT signer_id FROM participants WHERE signer_id='signer_tx';").fetchone()
        assert row is not None

    # Test rollback on exception
    with pytest.raises(ValueError, match="Simulated error"), db.transaction() as conn:
        conn.execute(
            "INSERT INTO participants (signer_id, metadata_schema_version, created_at_utc) "
            "VALUES ('signer_rollback', '1.0.0', '2026-11-06T10:00:00Z');"
        )
        raise ValueError("Simulated error")

    # Verify signer_rollback was NOT committed
    with db.read_connection() as conn:
        row = conn.execute("SELECT signer_id FROM participants WHERE signer_id='signer_rollback';").fetchone()
        assert row is None


def test_database_foreign_key_violation_in_transaction(tmp_path: Path):
    db_file = tmp_path / "test_fk.db"
    db = CorpusDatabase(db_file)

    # Inserting consent with nonexistent participant violates foreign key
    with pytest.raises(sqlite3.IntegrityError), db.transaction() as conn:
        conn.execute(
            "INSERT INTO consents (consent_id, signer_id, form_version, signed_at_utc, evidence_sha256, status) "
            "VALUES ('c1', 'nonexistent_signer', '1.0.0', '2026-11-06T10:00:00Z', 'hash', 'active');"
        )


def test_database_backup_and_integrity_checks(tmp_path: Path):
    db_file = tmp_path / "source.db"
    db = CorpusDatabase(db_file)

    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO participants (signer_id, metadata_schema_version, created_at_utc) "
            "VALUES ('signer_backup', '1.0.0', '2026-11-06T10:00:00Z');"
        )

    # Run integrity and foreign key check
    diag = db.integrity_check()
    assert diag == ("ok",)
    fk_violations = db.foreign_key_check()
    assert fk_violations == ()

    # Test live backup
    backup_file = tmp_path / "backup.db"
    db.backup(backup_file)
    assert backup_file.is_file()

    # Verify content in backup file
    backup_db = CorpusDatabase(backup_file)
    with backup_db.read_connection() as conn:
        val = conn.execute("SELECT signer_id FROM participants WHERE signer_id='signer_backup';").fetchone()[0]
        assert val == "signer_backup"
