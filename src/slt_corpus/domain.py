"""Domain models and contracts for the SLT Corpus package.

Implements typed entities for participants, consent records, sessions,
recordings, assets, annotations, lexical entries, and dataset releases.
Enforces strict invariants including ISO-8601 UTC timestamp validation,
path safety, and pseudonymity.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath

# Disallowed direct identifier patterns in participant metadata
PROHIBITED_METADATA_KEYS = frozenset({
    "name",
    "first_name",
    "last_name",
    "full_name",
    "real_name",
    "email",
    "phone",
    "telephone",
    "cellphone",
    "cedula",
    "documento",
    "identificacion",
    "id_number",
    "address",
    "direccion",
    "social_security",
})

HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")
PSEUDONYM_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")


class CorpusValidationError(ValueError):
    """Raised when a corpus domain contract or invariant is violated."""


class ConsentPurpose(StrEnum):
    """Purposes for which data usage may be authorized."""

    RECORD_AND_STORE = "record_and_store"
    DERIVE_LANDMARKS = "derive_landmarks"
    INTERNAL_RESEARCH = "internal_research"
    NONCOMMERCIAL_TRAINING = "noncommercial_training"
    COMMERCIAL_TRAINING = "commercial_training"
    SHARE_WITH_PARTNERS = "share_with_partners"
    PUBLISH_RAW_VIDEO = "publish_raw_video"
    PUBLISH_DERIVED_DATA = "publish_derived_data"


class RecordingStatus(StrEnum):
    """Lifecycle status of a recording."""

    INGESTED = "ingested"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class AnnotationStatus(StrEnum):
    """Lifecycle status of an annotation or document."""

    DRAFT = "draft"
    REVIEWED = "reviewed"
    ADJUDICATED = "adjudicated"
    REJECTED = "rejected"


class BoundaryQuality(StrEnum):
    """Temporal boundary precision indicator."""

    EXACT = "exact"
    APPROXIMATE = "approximate"
    UNVERIFIED = "unverified"


class ReleaseApprovalStatus(StrEnum):
    """Approval status of a dataset release."""

    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


def validate_iso8601_utc(timestamp_str: str, field_name: str = "timestamp") -> None:
    """Validate that a string represents a valid ISO-8601 datetime with a timezone.

    Raises:
        CorpusValidationError: If parsing fails or the datetime is naive (lacks tz).
    """
    if not isinstance(timestamp_str, str) or not timestamp_str.strip():
        raise CorpusValidationError(f"{field_name} must be a non-empty string.")
    try:
        # Normalize trailing Z to +00:00 for robust parsing across Python versions
        normalized = (
            timestamp_str[:-1] + "+00:00"
            if timestamp_str.endswith("Z")
            else timestamp_str
        )
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            raise CorpusValidationError(
                f"{field_name} must specify a timezone offset (e.g. +00:00 or Z)."
            )
    except CorpusValidationError:
        raise
    except Exception as exc:
        raise CorpusValidationError(
            f"{field_name} is not a valid ISO-8601 timestamp with timezone: {timestamp_str!r}"
        ) from exc


def validate_relative_path(path_str: str, field_name: str = "path") -> None:
    """Validate that a path is relative, normalized, and prevents traversal attacks.

    Rejects:
      - Null bytes
      - Backslashes (enforcing forward slashes for cross-platform storage)
      - Directory traversal segments ('..')
      - Absolute paths (leading '/')
    """
    if not isinstance(path_str, str) or not path_str.strip():
        raise CorpusValidationError(f"{field_name} must be a non-empty string.")
    if "\0" in path_str:
        raise CorpusValidationError(f"{field_name} contains forbidden null byte.")
    if "\\" in path_str:
        raise CorpusValidationError(
            f"{field_name} contains backslashes; use forward slashes for storage paths."
        )
    posix_path = PurePosixPath(path_str)
    if posix_path.is_absolute():
        raise CorpusValidationError(f"{field_name} must be relative, not absolute.")
    for part in posix_path.parts:
        if part in ("..", "."):
            raise CorpusValidationError(
                f"{field_name} contains directory traversal element: {part!r}"
            )


def validate_fps(fps_num: int | None, fps_den: int | None) -> None:
    """Ensure fps_num and fps_den are either both None or both positive integers."""
    if fps_num is None and fps_den is None:
        return
    if fps_num is None or fps_den is None:
        raise CorpusValidationError(
            "fps_num and fps_den must both be None or both be positive integers."
        )
    if not isinstance(fps_num, int) or not isinstance(fps_den, int):
        raise CorpusValidationError("fps_num and fps_den must be integers.")
    if fps_num <= 0 or fps_den <= 0:
        raise CorpusValidationError("fps_num and fps_den must be strictly positive (> 0).")


def validate_sha256_hash(hash_str: str, field_name: str = "sha256") -> None:
    """Validate 64-character lowercase hex SHA-256 string."""
    if not isinstance(hash_str, str) or not HEX64_REGEX.match(hash_str):
        raise CorpusValidationError(
            f"{field_name} must be a 64-character lowercase hexadecimal SHA-256 digest."
        )


def validate_pseudonym_id(signer_id: str, field_name: str = "signer_id") -> None:
    """Ensure participant ID is a valid alphanumeric slug and not a direct identifier."""
    if not isinstance(signer_id, str) or not signer_id.strip():
        raise CorpusValidationError(f"{field_name} must be a non-empty string.")
    if "@" in signer_id:
        raise CorpusValidationError(f"{field_name} appears to be an email address.")
    if not PSEUDONYM_REGEX.match(signer_id):
        raise CorpusValidationError(
            f"{field_name} must contain only alphanumeric characters, dashes, and underscores."
        )


def validate_no_direct_identifiers(metadata_json: str) -> None:
    """Validate that participant metadata does not contain direct personal identifier keys."""
    if not metadata_json.strip():
        return
    try:
        data = json.loads(metadata_json)
        if not isinstance(data, dict):
            raise CorpusValidationError("metadata_json must represent a JSON object.")
        lower_keys = {str(k).lower().strip() for k in data}
        found_prohibited = lower_keys.intersection(PROHIBITED_METADATA_KEYS)
        if found_prohibited:
            raise CorpusValidationError(
                f"Direct personal identifiers prohibited in metadata: {sorted(found_prohibited)}"
            )
    except json.JSONDecodeError as exc:
        raise CorpusValidationError("metadata_json is not valid JSON.") from exc


@dataclass(frozen=True, slots=True)
class Participant:
    """Pseudonymous participant registry record."""

    signer_id: str
    metadata_json: str
    created_at_utc: str

    def __post_init__(self) -> None:
        validate_pseudonym_id(self.signer_id, "signer_id")
        validate_no_direct_identifiers(self.metadata_json)
        validate_iso8601_utc(self.created_at_utc, "created_at_utc")


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    """Purpose-specific informed consent authorization."""

    consent_id: str
    signer_id: str
    form_version: str
    signed_at_utc: str
    granted_purposes: frozenset[ConsentPurpose]
    evidence_sha256: str
    revoked_at_utc: str | None = None

    def __post_init__(self) -> None:
        if not self.consent_id.strip():
            raise CorpusValidationError("consent_id cannot be empty.")
        validate_pseudonym_id(self.signer_id, "signer_id")
        if not self.form_version.strip():
            raise CorpusValidationError("form_version cannot be empty.")
        validate_iso8601_utc(self.signed_at_utc, "signed_at_utc")
        if self.revoked_at_utc is not None:
            validate_iso8601_utc(self.revoked_at_utc, "revoked_at_utc")
        validate_sha256_hash(self.evidence_sha256, "evidence_sha256")
        if not self.granted_purposes:
            raise CorpusValidationError("ConsentRecord must grant at least one purpose.")

    def permits(self, purpose: ConsentPurpose) -> bool:
        """Check if purpose is authorized and consent has not been revoked."""
        if self.revoked_at_utc is not None:
            return False
        return purpose in self.granted_purposes


@dataclass(frozen=True, slots=True)
class Session:
    """Capture session record associating participant, protocol, and operator."""

    session_id: str
    signer_id: str
    protocol_id: str
    recorded_at_utc: str
    operator_id: str
    metadata_json: str = "{}"

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise CorpusValidationError("session_id cannot be empty.")
        validate_pseudonym_id(self.signer_id, "signer_id")
        if not self.protocol_id.strip():
            raise CorpusValidationError("protocol_id cannot be empty.")
        validate_iso8601_utc(self.recorded_at_utc, "recorded_at_utc")
        if not self.operator_id.strip():
            raise CorpusValidationError("operator_id cannot be empty.")


@dataclass(frozen=True, slots=True)
class Recording:
    """Raw media recording registered in the corpus."""

    recording_id: str
    session_id: str
    signer_id: str
    source_video_sha256: str
    storage_relative_path: str
    duration_ns: int
    fps_num: int | None
    fps_den: int | None
    width: int
    height: int
    container_format: str
    video_codec: str
    status: RecordingStatus = RecordingStatus.INGESTED
    parent_recording_id: str | None = None
    metadata_json: str = "{}"

    def __post_init__(self) -> None:
        if not self.recording_id.strip():
            raise CorpusValidationError("recording_id cannot be empty.")
        if not self.session_id.strip():
            raise CorpusValidationError("session_id cannot be empty.")
        validate_pseudonym_id(self.signer_id, "signer_id")
        validate_sha256_hash(self.source_video_sha256, "source_video_sha256")
        validate_relative_path(self.storage_relative_path, "storage_relative_path")
        if self.duration_ns <= 0:
            raise CorpusValidationError("duration_ns must be strictly positive.")
        validate_fps(self.fps_num, self.fps_den)
        if self.width <= 0 or self.height <= 0:
            raise CorpusValidationError("width and height must be positive dimensions.")
        if not self.container_format.strip():
            raise CorpusValidationError("container_format cannot be empty.")
        if not self.video_codec.strip():
            raise CorpusValidationError("video_codec cannot be empty.")


@dataclass(frozen=True, slots=True)
class Asset:
    """Derived artifact (e.g. landmarks, features) associated with a recording."""

    asset_id: str
    parent_recording_id: str
    asset_type: str
    storage_relative_path: str
    sha256: str
    extractor_name: str | None = None
    extractor_version: str | None = None
    model_sha256: str | None = None
    configuration_hash: str | None = None
    created_at_utc: str = ""

    def __post_init__(self) -> None:
        if not self.asset_id.strip():
            raise CorpusValidationError("asset_id cannot be empty.")
        if not self.parent_recording_id.strip():
            raise CorpusValidationError("parent_recording_id cannot be empty.")
        if not self.asset_type.strip():
            raise CorpusValidationError("asset_type cannot be empty.")
        validate_relative_path(self.storage_relative_path, "storage_relative_path")
        validate_sha256_hash(self.sha256, "sha256")
        if self.model_sha256 is not None:
            validate_sha256_hash(self.model_sha256, "model_sha256")
        if self.created_at_utc:
            validate_iso8601_utc(self.created_at_utc, "created_at_utc")


@dataclass(frozen=True, slots=True)
class Annotation:
    """Linguistic annotation bounded by a semi-open nanosecond interval [start_ns, end_ns)."""

    annotation_id: str
    document_id: str
    tier_id: str
    start_ns: int
    end_ns: int
    value: str
    parent_annotation_id: str | None = None
    boundary_quality: BoundaryQuality = BoundaryQuality.UNVERIFIED
    status: AnnotationStatus = AnnotationStatus.DRAFT
    annotator_id: str | None = None
    revision: int = 1

    def __post_init__(self) -> None:
        if not self.annotation_id.strip():
            raise CorpusValidationError("annotation_id cannot be empty.")
        if not self.document_id.strip():
            raise CorpusValidationError("document_id cannot be empty.")
        if not self.tier_id.strip():
            raise CorpusValidationError("tier_id cannot be empty.")
        if self.start_ns < 0:
            raise CorpusValidationError("start_ns cannot be negative.")
        if self.end_ns <= self.start_ns:
            raise CorpusValidationError(
                f"Semi-open interval invariant violated: start_ns ({self.start_ns}) "
                f"must be strictly less than end_ns ({self.end_ns})."
            )
        if not isinstance(self.value, str):
            raise CorpusValidationError("Annotation value must be a string.")
        if self.revision < 1:
            raise CorpusValidationError("Annotation revision must be >= 1.")


@dataclass(frozen=True, slots=True)
class AnnotationDocument:
    """Container document for annotations corresponding to a recording."""

    document_id: str
    recording_id: str
    schema_version: str
    eaf_source_path: str | None
    created_at_utc: str
    status: AnnotationStatus = AnnotationStatus.DRAFT

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise CorpusValidationError("document_id cannot be empty.")
        if not self.recording_id.strip():
            raise CorpusValidationError("recording_id cannot be empty.")
        if not self.schema_version.strip():
            raise CorpusValidationError("schema_version cannot be empty.")
        if self.eaf_source_path is not None:
            validate_relative_path(self.eaf_source_path, "eaf_source_path")
        validate_iso8601_utc(self.created_at_utc, "created_at_utc")


@dataclass(frozen=True, slots=True)
class AnnotationReview:
    """Independent review record for an annotation."""

    review_id: str
    annotation_id: str
    reviewer_id: str
    status: AnnotationStatus
    comments: str
    reviewed_at_utc: str

    def __post_init__(self) -> None:
        if not self.review_id.strip():
            raise CorpusValidationError("review_id cannot be empty.")
        if not self.annotation_id.strip():
            raise CorpusValidationError("annotation_id cannot be empty.")
        if not self.reviewer_id.strip():
            raise CorpusValidationError("reviewer_id cannot be empty.")
        validate_iso8601_utc(self.reviewed_at_utc, "reviewed_at_utc")


@dataclass(frozen=True, slots=True)
class LexicalEntry:
    """Standardized lexical entry representing an LSC sign or grammatical token."""

    lexical_id: str
    gloss_lsc: str
    es_translations: tuple[str, ...]
    en_translations: tuple[str, ...]
    handshape_l: str | None = None
    handshape_r: str | None = None
    movement: str | None = None
    orientation: str | None = None
    location: str | None = None
    is_two_handed: bool = False
    metadata_json: str = "{}"

    def __post_init__(self) -> None:
        if not self.lexical_id.strip():
            raise CorpusValidationError("lexical_id cannot be empty.")
        if not self.gloss_lsc.strip():
            raise CorpusValidationError("gloss_lsc cannot be empty.")
        if not self.es_translations:
            raise CorpusValidationError("Must provide at least one Spanish translation.")
        if not self.en_translations:
            raise CorpusValidationError("Must provide at least one English translation.")


@dataclass(frozen=True, slots=True)
class SplitAssignment:
    """Assignment of a recording and signer to a dataset split (e.g. train/val/test)."""

    split_id: str
    dataset_release_id: str
    split_name: str
    recording_id: str
    signer_id: str

    def __post_init__(self) -> None:
        if not self.split_id.strip():
            raise CorpusValidationError("split_id cannot be empty.")
        if not self.dataset_release_id.strip():
            raise CorpusValidationError("dataset_release_id cannot be empty.")
        if self.split_name not in ("train", "validation", "test"):
            raise CorpusValidationError(
                f"split_name must be 'train', 'validation', or 'test', got {self.split_name!r}"
            )
        if not self.recording_id.strip():
            raise CorpusValidationError("recording_id cannot be empty.")
        validate_pseudonym_id(self.signer_id, "signer_id")


@dataclass(frozen=True, slots=True)
class DatasetRelease:
    """Immutable release manifest specification."""

    release_id: str
    dataset_id: str
    dataset_version: str
    profile_id: str
    task: str
    created_at_utc: str
    corpus_version: str
    annotation_schema_version: str
    usage_scope: ConsentPurpose
    split_manifest_relpath: str
    approval_status: ReleaseApprovalStatus = ReleaseApprovalStatus.DRAFT
    source_recording_ids: tuple[str, ...] = ()
    annotation_document_ids: tuple[str, ...] = ()
    license_review_status: str = "pending"
    parent_release_id: str | None = None
    code_commit: str | None = None

    def __post_init__(self) -> None:
        if not self.release_id.strip():
            raise CorpusValidationError("release_id cannot be empty.")
        if not self.dataset_id.strip():
            raise CorpusValidationError("dataset_id cannot be empty.")
        if not self.dataset_version.strip():
            raise CorpusValidationError("dataset_version cannot be empty.")
        if not self.profile_id.strip():
            raise CorpusValidationError("profile_id cannot be empty.")
        if not self.task.strip():
            raise CorpusValidationError("task cannot be empty.")
        validate_iso8601_utc(self.created_at_utc, "created_at_utc")
        if not self.corpus_version.strip():
            raise CorpusValidationError("corpus_version cannot be empty.")
        if not self.annotation_schema_version.strip():
            raise CorpusValidationError("annotation_schema_version cannot be empty.")
        validate_relative_path(self.split_manifest_relpath, "split_manifest_relpath")
