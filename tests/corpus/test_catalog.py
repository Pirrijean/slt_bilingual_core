"""Unit tests for slt_corpus.catalog SQLite relational repository."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
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

TEST_HASH = "d" * 64


def test_catalog_foreign_key_enforcement(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)

    # Attempting to add a consent for a non-existent participant must fail under foreign keys
    consent = ConsentRecord(
        consent_id="c_001",
        signer_id="non_existent_signer",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00Z",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    with pytest.raises(sqlite3.IntegrityError):
        catalog.add_consent(consent)


def test_catalog_crud_and_relationships(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)

    # 1. Add Participant
    participant = Participant(
        signer_id="signer_001",
        metadata_json='{"dialect": "bogota"}',
        created_at_utc="2026-11-06T10:00:00Z",
    )
    catalog.add_participant(participant)
    fetched_p = catalog.get_participant("signer_001")
    assert fetched_p is not None
    assert fetched_p.signer_id == "signer_001"

    # 2. Add Consent
    consent = ConsentRecord(
        consent_id="c_001",
        signer_id="signer_001",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:05:00Z",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE, ConsentPurpose.INTERNAL_RESEARCH}),
        evidence_sha256=TEST_HASH,
    )
    catalog.add_consent(consent)
    fetched_c = catalog.get_latest_consent_for_signer("signer_001")
    assert fetched_c is not None
    assert fetched_c.consent_id == "c_001"
    assert fetched_c.permits(ConsentPurpose.INTERNAL_RESEARCH)

    # 3. Add Session
    session = Session(
        session_id="sess_001",
        signer_id="signer_001",
        protocol_id="continuous_v1",
        recorded_at_utc="2026-11-06T10:10:00Z",
        operator_id="op_01",
    )
    catalog.add_session(session)
    fetched_s = catalog.get_session("sess_001")
    assert fetched_s is not None
    assert fetched_s.session_id == "sess_001"

    # 4. Add Recording
    recording = Recording(
        recording_id="rec_001",
        session_id="sess_001",
        signer_id="signer_001",
        source_video_sha256=TEST_HASH,
        storage_relative_path="objects/sha256/dd/video.mp4",
        duration_ns=5_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
        status=RecordingStatus.INGESTED,
    )
    catalog.add_recording(recording)
    fetched_rec = catalog.get_recording("rec_001")
    assert fetched_rec is not None
    assert fetched_rec.recording_id == "rec_001"
    assert fetched_rec.width == 1920

    # 5. Add Annotation Document and Annotations
    doc = AnnotationDocument(
        document_id="doc_001",
        recording_id="rec_001",
        schema_version="1.0.0",
        eaf_source_path=None,
        created_at_utc="2026-11-06T10:15:00Z",
    )
    catalog.add_annotation_document(doc)

    anns = [
        Annotation(
            annotation_id="ann_01",
            document_id="doc_001",
            tier_id="sign_token",
            start_ns=100_000_000,
            end_ns=800_000_000,
            value="HOLA",
            boundary_quality=BoundaryQuality.EXACT,
            status=AnnotationStatus.REVIEWED,
            revision=1,
        ),
        Annotation(
            annotation_id="ann_02",
            document_id="doc_001",
            tier_id="translation_es",
            start_ns=100_000_000,
            end_ns=800_000_000,
            value="hola",
            parent_annotation_id="ann_01",
            boundary_quality=BoundaryQuality.EXACT,
            status=AnnotationStatus.ADJUDICATED,
            revision=1,
        ),
    ]
    catalog.add_annotations(anns)
    fetched_anns = catalog.get_annotations_for_document("doc_001")
    assert len(fetched_anns) == 2
    assert fetched_anns[0].value == "HOLA"
    assert fetched_anns[1].value == "hola"


def test_catalog_atomic_backup(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)
    p = Participant(signer_id="signer_backup_01", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    catalog.add_participant(p)

    backup_file = tmp_path / "backups" / "catalog_backup.sqlite3"
    catalog.create_backup(backup_file)

    assert backup_file.is_file()
    # Read backup with a new catalog instance
    backup_cat = CorpusCatalog(backup_file)
    restored_p = backup_cat.get_participant("signer_backup_01")
    assert restored_p is not None
    assert restored_p.signer_id == "signer_backup_01"
