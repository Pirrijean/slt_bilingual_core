"""Quality assurance, inter-annotator agreement, and integrity validation for corpus recordings and annotations."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from slt_corpus.domain import Annotation, Recording
from slt_corpus.hashing import sha256_file


class QualityCheckError(ValueError):
    """Raised when technical quality or integrity validation fails."""


@dataclass(frozen=True, slots=True)
class QualityAssessment:
    """Multi-dimensional quality evaluation separating technical and linguistic health."""

    recording_id: str
    technical_status: str  # "approved", "needs_review", "rejected"
    linguistic_status: str  # "approved", "needs_review", "rejected"
    annotation_status: str  # "submitted", "reviewed", "adjudicated", "rejected"
    consent_status: str  # "valid", "revoked", "missing"
    dataset_eligibility: str  # "approved", "not_approved", "research_only"
    quality_flags: tuple[str, ...] = field(default_factory=tuple)


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


# ---------------------------------------------------------------------------
# Inter-Annotator Agreement & Boundary Consistency (Section 17.3)
# ---------------------------------------------------------------------------
def compute_temporal_iou(
    start_a_ns: int,
    end_a_ns: int,
    start_b_ns: int,
    end_b_ns: int,
) -> float:
    """Calculate temporal Intersection-over-Union (IoU) between two intervals.

    IoU = |A ∩ B| / |A ∪ B|
    """
    inter_start = max(start_a_ns, start_b_ns)
    inter_end = min(end_a_ns, end_b_ns)
    intersection = max(0, inter_end - inter_start)

    union_start = min(start_a_ns, start_b_ns)
    union_end = max(end_a_ns, end_b_ns)
    union = max(0, union_end - union_start)

    if union == 0:
        return 0.0
    return float(intersection) / float(union)


def compute_boundary_errors(
    start_a_ns: int,
    end_a_ns: int,
    start_b_ns: int,
    end_b_ns: int,
) -> tuple[int, int]:
    """Calculate absolute boundary discrepancies: (E_start, E_end) in nanoseconds."""
    e_start = abs(start_a_ns - start_b_ns)
    e_end = abs(end_a_ns - end_b_ns)
    return e_start, e_end


def compute_categorical_agreement(
    labels_a: Sequence[str],
    labels_b: Sequence[str],
) -> float:
    """Compute observed categorical agreement proportion P_o between two annotator series."""
    if not labels_a or len(labels_a) != len(labels_b):
        raise ValueError("Labels sequences must be non-empty and of identical length.")
    matches = sum(1 for a, b in zip(labels_a, labels_b, strict=True) if a == b)
    return float(matches) / float(len(labels_a))
