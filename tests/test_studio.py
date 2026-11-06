"""Unit and headless UI tests for slt_studio Dataset Studio."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    AlignmentKind,
    Annotation,
    AnnotationDocument,
    AnnotationStatus,
    BoundaryQuality,
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


def test_studio_main_window_lifecycle(qapp, tmp_path: Path, monkeypatch):
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", lambda *a, **kw: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.critical", lambda *a, **kw: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *a, **kw: None)
    monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.question", lambda *a, **kw: pytest.importorskip("PySide6.QtWidgets").QMessageBox.StandardButton.Yes)

    db_path = tmp_path / "studio_catalog.sqlite3"
    catalog = CorpusCatalog(db_path)

    # Seed catalog with a participant, recording, and annotation document
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
    catalog.add_annotation_document(
        AnnotationDocument(
            document_id="doc_std",
            recording_id="rec_std",
            schema_version="1.0.0",
            eaf_source_path=None,
            created_at_utc="2026-11-06T10:00:00Z",
            status=AnnotationStatus.SUBMITTED,
        )
    )
    catalog.add_annotations([
        Annotation(
            annotation_id="ann_std_01",
            document_id="doc_std",
            recording_id="rec_std",
            tier_id="sign_token",
            alignment_kind=AlignmentKind.TIME_ALIGNED,
            start_ns=100_000_000,
            end_ns=800_000_000,
            value="HOLA_DRAFT",
            revision=1,
            status=AnnotationStatus.SUBMITTED,
            boundary_quality=BoundaryQuality.PRECISE,
        )
    ])

    window = DatasetStudioMainWindow(db_path=db_path)
    assert window.stack.count() == 11

    # Test navigation to each of the 11 screens
    for i in range(11):
        window.switch_screen(i)
        assert window.stack.currentIndex() == i

    # Dashboard check
    window.screen_dashboard.refresh()
    assert window.screen_dashboard.table_quarantine.rowCount() >= 3

    # Recordings screen check
    window.screen_recordings.refresh()
    assert window.screen_recordings.table.rowCount() == 1

    # Test recordings filter
    window.screen_recordings._filter_rows("rec_std")
    assert not window.screen_recordings.table.isRowHidden(0)
    window.screen_recordings._filter_rows("nonexistent_id")
    assert window.screen_recordings.table.isRowHidden(0)

    # Participants screen check and add
    window.screen_participants.refresh()
    assert window.screen_participants.table.rowCount() == 1
    window.screen_participants.input_signer_id.setText("signer_new_02")
    window.screen_participants._add_participant()
    assert window.screen_participants.table.rowCount() == 2

    # Consent screen check
    window.screen_consent.refresh()
    assert window.screen_consent.table.rowCount() == 1

    # Review screen check
    window.screen_review.refresh()
    assert window.screen_review.combo_recordings.count() >= 1

    # Adjudication screen check
    window.screen_adjudication.refresh()
    assert window.screen_adjudication.table.rowCount() == 1
    # Select row and apply adjudicated decision
    window.screen_adjudication.table.selectRow(0)
    window.screen_adjudication.input_value.setText("HOLA_FINAL")
    window.screen_adjudication._apply_decision()
    # Check that annotation was updated
    anns = catalog.list_annotations_for_recording("rec_std")
    assert anns[0].value == "HOLA_FINAL"
    assert anns[0].status == AnnotationStatus.ADJUDICATED

    # Builder screen draft generation
    splits_file = tmp_path / "test_splits.json"
    window.screen_builder.input_splits_path.setText(str(splits_file))
    window.screen_builder._generate_splits_draft()
    assert splits_file.is_file()

    # Splits validator screen check
    window.screen_splits.refresh()
    window.screen_splits.input_splits.setText(str(splits_file))
    window.screen_splits._validate_splits()
    assert "VALID" in window.screen_splits.output_console.toPlainText()

    window.close()
