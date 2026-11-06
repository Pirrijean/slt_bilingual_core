"""Unit and headless UI tests for slt_studio Dataset Studio."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    ConsentPurpose,
    ConsentRecord,
    Participant,
    Recording,
    RecordingStatus,
    Session,
)
from slt_studio.main_window import DatasetStudioMainWindow

TEST_HASH = "8" * 64


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_studio_main_window_lifecycle(qapp, tmp_path: Path):
    db_path = tmp_path / "studio_catalog.sqlite3"
    catalog = CorpusCatalog(db_path)

    # Seed catalog with a participant and recording
    catalog.add_participant(
        Participant(signer_id="signer_std", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    catalog.add_consent(
        ConsentRecord(
            consent_id="c_std",
            signer_id="signer_std",
            form_version="1.0.0",
            signed_at_utc="2026-11-06T10:00:00Z",
            granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE, ConsentPurpose.INTERNAL_RESEARCH}),
            evidence_sha256=TEST_HASH,
        )
    )
    catalog.add_session(
        Session("sess_std", "signer_std", "continuous_v1", "2026-11-06T10:00:00Z", "op_std")
    )
    catalog.add_recording(
        Recording(
            recording_id="rec_std",
            session_id="sess_std",
            signer_id="signer_std",
            source_video_sha256=TEST_HASH,
            storage_relative_path="objects/sha256/88/take.mp4",
            duration_ns=2_000_000_000,
            fps_num=30,
            fps_den=1,
            width=1920,
            height=1080,
            container_format="mp4",
            video_codec="h264",
            status=RecordingStatus.INGESTED,
        )
    )

    window = DatasetStudioMainWindow(db_path=db_path)
    assert window.stack.count() == 10

    # Test navigation to each screen
    for i in range(10):
        window.switch_screen(i)
        assert window.stack.currentIndex() == i

    # Dashboard check
    window.screen_dashboard.refresh()
    assert window.screen_dashboard.table_quarantine.rowCount() >= 3

    # Recordings screen check
    window.screen_recordings.refresh()
    assert window.screen_recordings.table.rowCount() == 1

    window.close()
