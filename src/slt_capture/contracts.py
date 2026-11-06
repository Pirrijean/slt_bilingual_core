"""Formal contracts for controlled acquisition sessions, frames, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CaptureSessionRequest:
    """Formal request specification to initiate a multi-task capture session."""

    session_id: str
    protocol_id: str
    signer_ids: tuple[str, ...]
    task_ids: tuple[str, ...]
    started_at_utc: datetime


@dataclass(frozen=True, slots=True)
class CaptureFrameMetadata:
    """Per-frame authoritative timing and container encoding metadata."""

    frame_index: int
    capture_timestamp_ns: int
    encoded_pts: int | None = None
    encoded_time_base_num: int | None = None
    encoded_time_base_den: int | None = None


@dataclass(frozen=True, slots=True)
class CaptureArtifact:
    """Complete output produced by a recording take, linking media and timestamp sidecar."""

    temporary_media_path: str
    timestamps_sidecar_path: str
    frame_count: int
    source_frame_timestamps_preserved: bool
    media_sha256: str
    sidecar_sha256: str
