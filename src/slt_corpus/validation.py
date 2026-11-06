"""Quality assurance and integrity validation for corpus recordings and annotations."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from slt_corpus.domain import Annotation, Recording
from slt_corpus.hashing import sha256_file


class QualityCheckError(ValueError):
    """Raised when technical quality or integrity validation fails."""


def validate_recording_integrity(
    recording: Recording,
    storage_root: str | Path,
) -> None:
    """Verify that a recorded media file exists, is non-empty, and matches its catalog SHA-256."""
    root = Path(storage_root).resolve()
    target = (root / recording.storage_relative_path).resolve()

    if not target.is_file():
        raise QualityCheckError(
            f"Physical media file missing for recording {recording.recording_id!r} at {target}"
        )

    file_size = target.stat().st_size
    if file_size == 0:
        raise QualityCheckError(
            f"Physical media file is empty (0 bytes) for recording {recording.recording_id!r}"
        )

    actual_hash = sha256_file(target)
    if actual_hash != recording.source_video_sha256:
        raise QualityCheckError(
            f"Checksum mismatch for recording {recording.recording_id!r}: "
            f"expected {recording.source_video_sha256}, got {actual_hash}"
        )


def validate_annotation_tiers(
    annotations: Sequence[Annotation],
    allowed_tiers: set[str],
) -> None:
    """Validate that all annotations belong to recognized schema tier definitions."""
    for ann in annotations:
        if ann.tier_id not in allowed_tiers:
            raise QualityCheckError(
                f"Annotation {ann.annotation_id!r} uses unregistered tier {ann.tier_id!r}. "
                f"Allowed tiers: {sorted(allowed_tiers)}"
            )


def validate_annotation_temporal_bounds(
    annotations: Sequence[Annotation],
    max_duration_ns: int,
) -> None:
    """Validate that annotations do not exceed the parent recording's physical duration."""
    for ann in annotations:
        if ann.end_ns > max_duration_ns:
            raise QualityCheckError(
                f"Annotation {ann.annotation_id!r} end time ({ann.end_ns} ns) "
                f"exceeds recording duration ({max_duration_ns} ns)."
            )
