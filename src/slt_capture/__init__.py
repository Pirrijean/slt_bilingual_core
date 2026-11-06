"""SLT Capture Package: Controlled LSC sign acquisition and recording."""

from __future__ import annotations

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
    "CaptureProtocol",
    "CaptureRecorder",
    "CaptureSessionController",
    "EnvironmentMetadata",
    "ProtocolError",
    "ProtocolTask",
    "RecorderError",
    "SessionCaptureMetadata",
    "SessionState",
    "load_protocol_from_file",
]
