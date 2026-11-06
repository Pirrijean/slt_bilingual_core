"""SLT Corpus Package: Linguistic Corpus Engineering, Storage, and Governance.

Provides typed domain entities, purpose-specific consent verification,
content-addressed storage, relational catalog management, ELAN XML adaptation,
split disjointness validation, and release manifest construction.
"""

from __future__ import annotations

from slt_corpus.audit import CorpusAuditor
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.consent import (
    ConsentDeniedError,
    require_consent,
    validate_release_consent,
    validate_video_storage_scope,
)
from slt_corpus.domain import (
    Annotation,
    AnnotationDocument,
    AnnotationReview,
    AnnotationStatus,
    Asset,
    BoundaryQuality,
    ConsentPurpose,
    ConsentRecord,
    CorpusValidationError,
    DatasetRelease,
    LexicalEntry,
    Participant,
    Recording,
    RecordingStatus,
    ReleaseApprovalStatus,
    Session,
    SplitAssignment,
)
from slt_corpus.elan import EAFImportError, EAFRecord, import_eaf, to_slt_annotations
from slt_corpus.hashing import sha256_bytes, sha256_file, sha256_string
from slt_corpus.release import DatasetReleaseManager, ReleaseError
from slt_corpus.splits import (
    SplitValidationError,
    measure_sentence_overlap,
    validate_group_disjoint,
    validate_no_augmentation_leakage,
)
from slt_corpus.storage import (
    ALLOWED_EXTENSIONS,
    StorageError,
    StoredAsset,
    ingest_video,
)
from slt_corpus.validation import (
    QualityAssessment,
    QualityCheckError,
    compute_boundary_errors,
    compute_categorical_agreement,
    compute_temporal_iou,
    validate_annotation_temporal_bounds,
    validate_annotation_tiers,
    validate_recording_integrity,
)

__all__ = [
    "ALLOWED_EXTENSIONS",
    "Annotation",
    "AnnotationDocument",
    "AnnotationReview",
    "AnnotationStatus",
    "Asset",
    "BoundaryQuality",
    "ConsentDeniedError",
    "ConsentPurpose",
    "ConsentRecord",
    "CorpusAuditor",
    "CorpusCatalog",
    "CorpusValidationError",
    "DatasetRelease",
    "DatasetReleaseManager",
    "EAFImportError",
    "EAFRecord",
    "LexicalEntry",
    "Participant",
    "QualityAssessment",
    "QualityCheckError",
    "Recording",
    "RecordingStatus",
    "ReleaseApprovalStatus",
    "ReleaseError",
    "Session",
    "SplitAssignment",
    "SplitValidationError",
    "StorageError",
    "StoredAsset",
    "compute_boundary_errors",
    "compute_categorical_agreement",
    "compute_temporal_iou",
    "import_eaf",
    "ingest_video",
    "measure_sentence_overlap",
    "require_consent",
    "sha256_bytes",
    "sha256_file",
    "sha256_string",
    "to_slt_annotations",
    "validate_annotation_temporal_bounds",
    "validate_annotation_tiers",
    "validate_group_disjoint",
    "validate_no_augmentation_leakage",
    "validate_recording_integrity",
    "validate_release_consent",
    "validate_video_storage_scope",
]
