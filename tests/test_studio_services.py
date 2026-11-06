"""Unit tests for Dataset Studio backend services and worker runnables."""

from __future__ import annotations

from pathlib import Path

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    AnnotationStatus,
    ConsentPurpose,
    ConsentStatus,
    Participant,
    Recording,
    RecordingStatus,
    Session,
)
from slt_studio.services.adjudication_service import AdjudicationService
from slt_studio.services.annotation_service import AnnotationService
from slt_studio.services.corpus_service import CorpusService
from slt_studio.services.review_service import ReviewService
from slt_studio.workers.task_worker import WorkerRunnable

TEST_HASH = "a" * 64

SYNTHETIC_EAF = """<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT AUTHOR="annotator_1" FORMAT="3.0" VERSION="3.0">
    <TIME_ORDER>
        <TIME_SLOT TIME_SLOT_ID="ts1" TIME_VALUE="100"/>
        <TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="600"/>
    </TIME_ORDER>
    <TIER TIER_ID="sign_token">
        <ANNOTATION>
            <ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="ts1" TIME_SLOT_REF2="ts2">
                <ANNOTATION_VALUE>GRACIAS</ANNOTATION_VALUE>
            </ALIGNABLE_ANNOTATION>
        </ANNOTATION>
    </TIER>
</ANNOTATION_DOCUMENT>
"""


def test_corpus_service_crud_and_stats(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)
    service = CorpusService(catalog)

    # Add participant
    p = service.register_participant("signer_svc_01")
    assert p.signer_id == "signer_svc_01"
    assert len(service.get_participants()) == 1

    # Add consent
    c = service.register_consent(
        consent_id="c_svc_01",
        signer_id="signer_svc_01",
        form_version="1.0.0",
        purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    assert c.consent_id == "c_svc_01"
    assert len(service.get_consents()) == 1

    # Statistics
    stats = service.get_statistics()
    assert stats["participant_count"] == 1
    assert stats["active_consents"] == 1

    # Revoke
    service.revoke_consent("c_svc_01")
    consents = service.get_consents()
    assert consents[0].status == ConsentStatus.REVOKED


def test_annotation_service_and_adjudication_service(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)
    ann_service = AnnotationService(catalog)
    adj_service = AdjudicationService(catalog)

    # Register participant and recording
    catalog.add_participant(
        Participant(signer_id="signer_adj", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    catalog.add_session(
        Session("sess_adj", "signer_adj", "continuous_v1", "2026-11-06T10:00:00Z", "op_adj")
    )
    catalog.add_recording(
        Recording(
            recording_id="rec_adj",
            session_id="sess_adj",
            signer_id="signer_adj",
            source_video_sha256=TEST_HASH,
            storage_relative_path="objects/take.mp4",
            duration_ns=1_000_000_000,
            fps_num=30,
            fps_den=1,
            width=1920,
            height=1080,
            container_format="mp4",
            video_codec="h264",
            status=RecordingStatus.ANNOTATION_PENDING,
        )
    )

    eaf_file = tmp_path / "sample.eaf"
    eaf_file.write_text(SYNTHETIC_EAF, encoding="utf-8")

    anns = ann_service.import_elan_file(
        eaf_path=eaf_file,
        document_id="doc_adj",
        recording_id="rec_adj",
        annotator_id="ann_user_01",
    )
    assert len(anns) == 1
    assert anns[0].value == "GRACIAS"

    # Mark as submitted to be visible in adjudication
    with catalog._connect() as conn:
        conn.execute("UPDATE annotations SET status = 'submitted' WHERE document_id = 'doc_adj';")

    pending = adj_service.get_pending_adjudications()
    assert len(pending) == 1

    # Adjudicate
    adj_service.adjudicate_annotation(
        annotation_id=pending[0].annotation_id,
        adjudicated_value="GRACIAS_CORRECTED",
        new_status=AnnotationStatus.ADJUDICATED,
        adjudicator_id="linguist_expert",
    )
    updated = ann_service.get_annotations_for_recording("rec_adj")
    assert updated[0].value == "GRACIAS_CORRECTED"
    assert updated[0].status == AnnotationStatus.ADJUDICATED
    assert updated[0].revision == 2

    # Batch approve recording
    adj_service.approve_recording_annotations("rec_adj")
    rec = catalog.get_recording("rec_adj")
    assert rec is not None
    assert rec.status == RecordingStatus.APPROVED


def test_review_service_audit(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    storage_root = tmp_path / "storage"
    catalog = CorpusCatalog(db_path)
    service = ReviewService(catalog, storage_root)

    # Missing recording audit
    res_missing = service.audit_recording("nonexistent")
    assert res_missing.file_exists is False

    # Seed physical file
    target_rel = "objects/test.mp4"
    target_abs = storage_root / target_rel
    target_abs.parent.mkdir(parents=True, exist_ok=True)
    target_abs.write_bytes(b"some content")
    import hashlib
    h = hashlib.sha256(b"some content").hexdigest()

    catalog.add_participant(
        Participant(signer_id="signer_rev", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    catalog.add_session(
        Session("sess_rev", "signer_rev", "continuous_v1", "2026-11-06T10:00:00Z", "op_rev")
    )
    catalog.add_recording(
        Recording(
            recording_id="rec_rev",
            session_id="sess_rev",
            signer_id="signer_rev",
            source_video_sha256=h,
            storage_relative_path=target_rel,
            duration_ns=1_000_000_000,
            fps_num=30,
            fps_den=1,
            width=1920,
            height=1080,
            container_format="mp4",
            video_codec="h264",
            status=RecordingStatus.INGESTED,
        )
    )

    res = service.audit_recording("rec_rev")
    assert res.file_exists is True
    assert res.is_non_empty is True
    assert res.checksum_matches is True


def test_worker_runnable():
    def compute(x: int, y: int) -> int:
        return x + y

    worker = WorkerRunnable(compute, 10, 25)
    captured = {}

    def on_result(val):
        captured["result"] = val

    worker.signals.result.connect(on_result)
    worker.run()

    assert captured.get("result") == 35
