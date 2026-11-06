"""Unit tests for capture timing sidecar preservation and IngestService."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from slt_capture.contracts import (
    CaptureArtifact,
)
from slt_capture.ingest_service import CaptureIngestService, IngestError
from slt_capture.protocol import load_protocol_from_file
from slt_capture.recorder import CaptureRecorder
from slt_capture.session import CaptureSessionController
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    ConsentPurpose,
    ConsentRecord,
    Participant,
    Session,
)

TEST_HASH = "9" * 64


def test_capture_timestamp_sidecar_generation(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    storage_root = tmp_path / "storage"
    catalog = CorpusCatalog(db_path)

    catalog.add_participant(
        Participant(signer_id="signer_sidecar", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    consent = ConsentRecord(
        consent_id="c_sidecar",
        signer_id="signer_sidecar",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00Z",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    catalog.add_consent(consent)

    protocol = load_protocol_from_file("corpus/lsc/capture_protocols/continuous_v1.json")
    ctrl = CaptureSessionController(catalog, "sess_sc", "signer_sidecar", protocol, "op_sc")
    ctrl.register_in_catalog()

    recorder = CaptureRecorder(
        session_controller=ctrl,
        output_temp_dir=tmp_path / "temp",
        storage_root=storage_root,
    )
    recorder.start("take_sc_01", width=320, height=240, fps=30.0)

    # Write 3 frames with explicit monotonic timestamps
    base_ts = 1_000_000_000
    for i in range(3):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        recorder.write_frame(frame, capture_timestamp_ns=base_ts + i * 33_333_333)

    recording = recorder.stop("take_sc_01")
    assert recording.recording_id == "take_sc_01"
    artifact = recorder.last_artifact

    assert artifact is not None
    assert artifact.frame_count == 3
    assert artifact.source_frame_timestamps_preserved is True
    assert Path(artifact.timestamps_sidecar_path).is_file()

    # Verify sidecar contents
    sidecar_data = json.loads(Path(artifact.timestamps_sidecar_path).read_text(encoding="utf-8"))
    assert sidecar_data["frame_count"] == 3
    assert len(sidecar_data["frames"]) == 3
    assert sidecar_data["frames"][0]["capture_timestamp_ns"] == base_ts
    assert sidecar_data["frames"][1]["capture_timestamp_ns"] == base_ts + 33_333_333


def test_ingest_service_validation_and_registration(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    storage_root = tmp_path / "storage"
    catalog = CorpusCatalog(db_path)

    catalog.add_participant(
        Participant(signer_id="signer_ing", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    consent = ConsentRecord(
        consent_id="c_ing",
        signer_id="signer_ing",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00Z",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    catalog.add_consent(consent)
    catalog.add_session(
        Session("sess_ing_01", "signer_ing", "continuous_v1", "2026-11-06T10:00:00Z", "op_ing")
    )

    ingest_svc = CaptureIngestService(catalog, storage_root)

    # Create dummy media and sidecar files
    media_file = tmp_path / "dummy.mp4"
    media_file.write_bytes(b"dummy video binary content")
    import hashlib
    hasher = hashlib.sha256()
    hasher.update(b"dummy video binary content")
    media_sha = hasher.hexdigest()

    sidecar_file = tmp_path / "dummy.timestamps.json"
    sidecar_content = json.dumps({"frames": [{"capture_timestamp_ns": 100}, {"capture_timestamp_ns": 200}]})
    sidecar_file.write_text(sidecar_content, encoding="utf-8")
    hasher_sc = hashlib.sha256()
    hasher_sc.update(sidecar_content.encode("utf-8"))
    sidecar_sha = hasher_sc.hexdigest()

    artifact = CaptureArtifact(
        temporary_media_path=str(media_file),
        timestamps_sidecar_path=str(sidecar_file),
        frame_count=2,
        source_frame_timestamps_preserved=True,
        media_sha256=media_sha,
        sidecar_sha256=sidecar_sha,
    )

    rec = ingest_svc.ingest_capture_artifact(
        artifact=artifact,
        recording_id="rec_ing_01",
        session_id="sess_ing_01",
        signer_id="signer_ing",
        consent=consent,
        width=1920,
        height=1080,
    )

    assert rec.recording_id == "rec_ing_01"
    assert rec.source_video_sha256 == media_sha

    # Verify corrupt checksum raises IngestError
    corrupt_artifact = CaptureArtifact(
        temporary_media_path=str(media_file),
        timestamps_sidecar_path=str(sidecar_file),
        frame_count=2,
        source_frame_timestamps_preserved=True,
        media_sha256="wrong_checksum",
        sidecar_sha256=sidecar_sha,
    )
    with pytest.raises(IngestError, match="Media checksum mismatch"):
        ingest_svc.ingest_capture_artifact(
            artifact=corrupt_artifact,
            recording_id="rec_bad",
            session_id="sess_ing_01",
            signer_id="signer_ing",
            consent=consent,
            width=1920,
            height=1080,
        )
