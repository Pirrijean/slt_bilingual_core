"""SLT Capture Package: Controlled LSC sign acquisition, timing sidecars, and ingestion."""

from __future__ import annotations

from slt_capture.contracts import (
    CaptureArtifact,
    CaptureFrameMetadata,
    CaptureSessionRequest,
)
from slt_capture.ingest_service import CaptureIngestService, IngestError
from slt_capture.metadata import (
    CameraMetadata,
    EnvironmentMetadata,
    SessionCaptureMetadata,
)
from slt_capture.protocol import (
    CaptureProtocol,
    ProtocolError,
    ProtocolTask,
    load_protocol_from_file,
)
from slt_capture.recorder import CaptureRecorder, RecorderError
from slt_capture.session import CaptureSessionController, SessionState

__all__ = [
    "CameraMetadata",
    "CaptureArtifact",
    "CaptureFrameMetadata",
    "CaptureIngestService",
    "CaptureProtocol",
    "CaptureRecorder",
    "CaptureSessionController",
    "CaptureSessionRequest",
    "EnvironmentMetadata",
    "IngestError",
    "ProtocolError",
    "ProtocolTask",
    "RecorderError",
    "SessionCaptureMetadata",
    "SessionState",
    "load_protocol_from_file",
]
