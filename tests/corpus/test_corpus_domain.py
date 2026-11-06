"""Unit tests for slt_corpus.domain contracts and invariants."""

from __future__ import annotations

import pytest

from slt_corpus.domain import (
    Annotation,
    AnnotationStatus,
    BoundaryQuality,
    CorpusValidationError,
    Participant,
    validate_fps,
    validate_iso8601_utc,
    validate_relative_path,
)

VALID_HASH = "a" * 64


def test_iso8601_utc_validation():
    # Valid timestamps with timezone
    validate_iso8601_utc("2026-11-06T10:00:00+00:00")
    validate_iso8601_utc("2026-11-06T10:00:00Z")
    validate_iso8601_utc("2026-11-06T05:00:00-05:00")

    # Invalid: naive timestamp (no timezone)
    with pytest.raises(CorpusValidationError, match="timezone offset"):
        validate_iso8601_utc("2026-11-06 10:00:00")

    # Invalid: malformed string or empty
    with pytest.raises(CorpusValidationError):
        validate_iso8601_utc("")
    with pytest.raises(CorpusValidationError):
        validate_iso8601_utc("not-a-date")


def test_relative_path_safety():
    # Valid relative POSIX path
    validate_relative_path("objects/sha256/ab/abcdef.mp4")
    validate_relative_path("splits.json")

    # Forbidden: directory traversal
    with pytest.raises(CorpusValidationError, match="directory traversal"):
        validate_relative_path("../secret.mp4")
    with pytest.raises(CorpusValidationError, match="directory traversal"):
        validate_relative_path("objects/../../secret.mp4")

    # Forbidden: backslashes
    with pytest.raises(CorpusValidationError, match="backslashes"):
        validate_relative_path("objects\\sha256\\ab.mp4")

    # Forbidden: null byte
    with pytest.raises(CorpusValidationError, match="null byte"):
        validate_relative_path("objects/\0bad.mp4")

    # Forbidden: absolute path
    with pytest.raises(CorpusValidationError, match="must be relative"):
        validate_relative_path("/root/video.mp4")


def test_fps_validation():
    # Both None is valid
    validate_fps(None, None)
    # Both positive integers is valid
    validate_fps(30, 1)
    validate_fps(30000, 1001)

    # Partial None is rejected
    with pytest.raises(CorpusValidationError):
        validate_fps(30, None)
    with pytest.raises(CorpusValidationError):
        validate_fps(None, 1)

    # Zero or negative is rejected
    with pytest.raises(CorpusValidationError):
        validate_fps(0, 1)
    with pytest.raises(CorpusValidationError):
        validate_fps(30, -1)


def test_participant_direct_identifier_rejection():
    # Valid pseudonymous participant
    p = Participant(
        signer_id="signer_lsc_001",
        metadata_json='{"age_bracket": "20-30", "dominant_hand": "right"}',
        created_at_utc="2026-11-06T00:00:00Z",
    )
    assert p.signer_id == "signer_lsc_001"

    # Reject email in signer_id
    with pytest.raises(CorpusValidationError, match="email address"):
        Participant(
            signer_id="user@example.com",
            metadata_json="{}",
            created_at_utc="2026-11-06T00:00:00Z",
        )

    # Reject direct personal identifiers in metadata keys
    with pytest.raises(CorpusValidationError, match="Direct personal identifiers prohibited"):
        Participant(
            signer_id="signer_001",
            metadata_json='{"real_name": "Juan Perez", "age": 25}',
            created_at_utc="2026-11-06T00:00:00Z",
        )
    with pytest.raises(CorpusValidationError, match="Direct personal identifiers prohibited"):
        Participant(
            signer_id="signer_001",
            metadata_json='{"cedula": "12345678"}',
            created_at_utc="2026-11-06T00:00:00Z",
        )


def test_annotation_semi_open_interval():
    # Valid interval [1000, 2000)
    ann = Annotation(
        annotation_id="ann_001",
        document_id="doc_001",
        tier_id="sign_token",
        start_ns=1000,
        end_ns=2000,
        value="HOLA",
        boundary_quality=BoundaryQuality.EXACT,
        status=AnnotationStatus.DRAFT,
        revision=1,
    )
    assert ann.end_ns > ann.start_ns

    # Invariant violation: start_ns == end_ns
    with pytest.raises(CorpusValidationError, match="Semi-open interval invariant"):
        Annotation(
            annotation_id="ann_002",
            document_id="doc_001",
            tier_id="sign_token",
            start_ns=1000,
            end_ns=1000,
            value="HOLA",
        )

    # Invariant violation: start_ns > end_ns
    with pytest.raises(CorpusValidationError, match="Semi-open interval invariant"):
        Annotation(
            annotation_id="ann_003",
            document_id="doc_001",
            tier_id="sign_token",
            start_ns=2000,
            end_ns=1000,
            value="HOLA",
        )

    # Revision must be >= 1
    with pytest.raises(CorpusValidationError, match="revision must be >= 1"):
        Annotation(
            annotation_id="ann_004",
            document_id="doc_001",
            tier_id="sign_token",
            start_ns=1000,
            end_ns=2000,
            value="HOLA",
            revision=0,
        )
