"""Unit tests for slt_corpus.audit and slt_corpus.cli execution."""

from __future__ import annotations

from pathlib import Path

from slt_corpus.audit import CorpusAuditor
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.cli import main as cli_main
from slt_corpus.domain import (
    ConsentPurpose,
    ConsentRecord,
    Participant,
    Recording,
    Session,
)

TEST_HASH = "f" * 64


def test_corpus_auditor_report(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)

    # 1. Add participants
    p1 = Participant(signer_id="s1", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    p2 = Participant(signer_id="s2", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    catalog.add_participant(p1)
    catalog.add_participant(p2)

    # 2. Add consents (1 active, 1 revoked)
    c1 = ConsentRecord(
        consent_id="c1",
        signer_id="s1",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00Z",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    c2 = ConsentRecord(
        consent_id="c2",
        signer_id="s2",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00Z",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
        revoked_at_utc="2026-11-06T12:00:00Z",
    )
    catalog.add_consent(c1)
    catalog.add_consent(c2)

    # 3. Add session and recordings (1 original, 1 augmented)
    sess = Session(
        session_id="sess_1",
        signer_id="s1",
        protocol_id="continuous_v1",
        recorded_at_utc="2026-11-06T10:00:00Z",
        operator_id="op_1",
    )
    catalog.add_session(sess)

    r1 = Recording(
        recording_id="rec_orig",
        session_id="sess_1",
        signer_id="s1",
        source_video_sha256=TEST_HASH,
        storage_relative_path="objects/sha256/ff/orig.mp4",
        duration_ns=2_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
    )
    r2 = Recording(
        recording_id="rec_aug",
        session_id="sess_1",
        signer_id="s1",
        source_video_sha256=TEST_HASH,
        storage_relative_path="objects/sha256/ff/aug.mp4",
        duration_ns=2_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
        parent_recording_id="rec_orig",
    )
    catalog.add_recording(r1)
    catalog.add_recording(r2)

    auditor = CorpusAuditor(catalog)
    report = auditor.generate_audit_report("corpus/lsc/documentation/external_datasets.json")

    summary = report["summary"]
    assert summary["total_participants"] == 2
    assert summary["total_recordings"] == 2
    assert summary["original_recordings"] == 1
    assert summary["augmented_recordings"] == 1
    assert summary["total_duration_seconds"] == 4.0

    gov = report["governance"]
    assert gov["active_consents"] == 1
    assert gov["revoked_consents"] == 1


def test_cli_end_to_end_flow(tmp_path: Path):
    db_file = tmp_path / "cli_catalog.sqlite3"
    storage_dir = tmp_path / "storage"

    # 1. Init CLI
    exit_code = cli_main(["init", "--root", str(tmp_path / "corpus"), "--db", str(db_file)])
    assert exit_code == 0

    # 2. Add Participant CLI
    exit_code = cli_main(
        ["participant", "add", "--signer-id", "signer_cli_01", "--db", str(db_file)]
    )
    assert exit_code == 0

    # 3. Add Consent CLI
    exit_code = cli_main(
        [
            "consent",
            "add",
            "--consent-id",
            "c_cli_01",
            "--signer-id",
            "signer_cli_01",
            "--form-version",
            "1.0.0",
            "--purposes",
            "record_and_store",
            "internal_research",
            "--evidence-sha256",
            TEST_HASH,
            "--db",
            str(db_file),
        ]
    )
    assert exit_code == 0

    # 4. Ingest video CLI
    sample_mp4 = tmp_path / "cli_sample.mp4"
    sample_mp4.write_bytes(b"cli-sample-video-content")

    # Ingest requires a valid session in catalog due to foreign keys
    catalog = CorpusCatalog(db_file)
    catalog.add_session(
        Session(
            session_id="sess_cli_01",
            signer_id="signer_cli_01",
            protocol_id="continuous_v1",
            recorded_at_utc="2026-11-06T10:00:00Z",
            operator_id="op_cli",
        )
    )

    exit_code = cli_main(
        [
            "ingest",
            "--file",
            str(sample_mp4),
            "--storage-root",
            str(storage_dir),
            "--signer-id",
            "signer_cli_01",
            "--consent-id",
            "c_cli_01",
            "--session-id",
            "sess_cli_01",
            "--recording-id",
            "rec_cli_01",
            "--db",
            str(db_file),
        ]
    )
    assert exit_code == 0

    # 5. Audit CLI
    exit_code = cli_main(["audit", "--db", str(db_file)])
    assert exit_code == 0
