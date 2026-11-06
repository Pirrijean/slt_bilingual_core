"""Unit tests for slt_capture package."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from slt_capture.metadata import (
    CameraMetadata,
    EnvironmentMetadata,
    SessionCaptureMetadata,
)
from slt_capture.protocol import load_protocol_from_file
from slt_capture.recorder import CaptureRecorder
from slt_capture.session import CaptureSessionController, SessionState
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.consent import ConsentDeniedError
from slt_corpus.domain import (
    ConsentPurpose,
    ConsentRecord,
    CorpusValidationError,
    Participant,
)

TEST_HASH = "7" * 64


def test_load_protocols():
    continuous_proto = load_protocol_from_file("corpus/lsc/capture_protocols/continuous_v1.json")
    assert continuous_proto.protocol_id == "lsc_continuous_v1"
    assert continuous_proto.mode == "continuous"
    assert len(continuous_proto.tasks) >= 2

    controlled_proto = load_protocol_from_file("corpus/lsc/capture_protocols/controlled_v1.json")
    assert controlled_proto.protocol_id == "lsc_controlled_v1"
    assert controlled_proto.mode == "controlled"
    assert len(controlled_proto.tasks) >= 2


def test_metadata_pii_rejection():
    cam = CameraMetadata("cam_01", "Webcam HD", 1920, 1080, 30.0, "dshow")
    env = EnvironmentMetadata("diffuse", 400, "grey", 150)

    # Valid metadata
    meta = SessionCaptureMetadata(
        session_id="sess_meta_01",
        signer_id="signer_001",
        protocol_id="continuous_v1",
        task_id="task_01",
        operator_id="op_01",
        recorded_at_utc="2026-11-06T10:00:00Z",
        camera=cam,
        environment=env,
        extra_properties_json='{"framing": "upper_body"}',
    )
    json_out = meta.to_json()
    assert "signer_001" in json_out

    # Direct PII in extra metadata rejected
    with pytest.raises(CorpusValidationError, match="Direct personal identifiers prohibited"):
        SessionCaptureMetadata(
            session_id="sess_bad",
            signer_id="signer_001",
            protocol_id="continuous_v1",
            task_id="task_01",
            operator_id="op_01",
            recorded_at_utc="2026-11-06T10:00:00Z",
            camera=cam,
            environment=env,
            extra_properties_json='{"real_name": "Alice"}',
        )


def test_session_controller_lifecycle_and_consent(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    catalog = CorpusCatalog(db_path)

    protocol = load_protocol_from_file("corpus/lsc/capture_protocols/continuous_v1.json")

    # Participant not in catalog raises ValueError
    with pytest.raises(ValueError, match="not registered in catalog"):
        CaptureSessionController(catalog, "sess_01", "unregistered", protocol, "op_01")

    # Register participant
    catalog.add_participant(
        Participant(signer_id="signer_01", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )

    # Missing consent raises ConsentDeniedError
    with pytest.raises(ConsentDeniedError, match="No consent record found"):
        CaptureSessionController(catalog, "sess_01", "signer_01", protocol, "op_01")

    # Add active consent
    catalog.add_consent(
        ConsentRecord(
            consent_id="c_01",
            signer_id="signer_01",
            form_version="1.0.0",
            signed_at_utc="2026-11-06T10:00:00Z",
            granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
            evidence_sha256=TEST_HASH,
        )
    )

    ctrl = CaptureSessionController(catalog, "sess_01", "signer_01", protocol, "op_01")
    assert ctrl.state == SessionState.READY

    task = ctrl.select_task(protocol.tasks[0].task_id)
    assert task == protocol.tasks[0]

    session_rec = ctrl.register_in_catalog()
    assert session_rec.session_id == "sess_01"


def test_capture_recorder_end_to_end(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    storage_root = tmp_path / "storage"
    catalog = CorpusCatalog(db_path)

    catalog.add_participant(
        Participant(signer_id="signer_rec", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    catalog.add_consent(
        ConsentRecord(
            consent_id="c_rec",
            signer_id="signer_rec",
            form_version="1.0.0",
            signed_at_utc="2026-11-06T10:00:00Z",
            granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
            evidence_sha256=TEST_HASH,
        )
    )
    protocol = load_protocol_from_file("corpus/lsc/capture_protocols/continuous_v1.json")
    ctrl = CaptureSessionController(catalog, "sess_rec_01", "signer_rec", protocol, "op_rec")
    ctrl.register_in_catalog()

    recorder = CaptureRecorder(
        session_controller=ctrl,
        output_temp_dir=tmp_path / "temp",
        storage_root=storage_root,
    )
    recorder.start("take_001", width=640, height=480, fps=30.0)

    # Write 5 frames
    for _ in range(5):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        recorder.write_frame(frame)

    recording = recorder.stop("take_001")
    assert recording.recording_id == "take_001"
    assert recording.width == 640
    assert recording.height == 480
    assert recording.source_video_sha256 is not None

    # Check catalog persistence
    fetched = catalog.get_recording("take_001")
    assert fetched is not None
    assert fetched.recording_id == "take_001"
