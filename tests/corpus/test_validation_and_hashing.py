"""Unit tests for slt_corpus.validation and slt_corpus.hashing."""

from __future__ import annotations

from pathlib import Path

import pytest

from slt_corpus.domain import (
    Annotation,
    Recording,
    RecordingStatus,
)
from slt_corpus.hashing import sha256_bytes, sha256_file, sha256_string
from slt_corpus.validation import (
    QualityCheckError,
    validate_annotation_temporal_bounds,
    validate_annotation_tiers,
    validate_recording_integrity,
)


def test_hashing_utilities(tmp_path: Path):
    data = b"test payload"
    expected_hex = "813ca5285c28ccee5cab8b10ebda9c908fd6d78ed9dc94cc65ea6cb67a7f13ae"
    assert sha256_bytes(data) == expected_hex
    assert sha256_string("test payload") == expected_hex

    test_file = tmp_path / "data.bin"
    test_file.write_bytes(data)
    assert sha256_file(test_file) == expected_hex

    # Invalid chunk size raises ValueError
    with pytest.raises(ValueError, match="strictly positive"):
        sha256_file(test_file, chunk_size=0)


def test_recording_integrity_checks(tmp_path: Path):
    storage_root = tmp_path / "storage"
    rel_path = "objects/sha256/27/27be97.mp4"
    abs_path = storage_root / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(b"test payload")
    correct_hash = sha256_bytes(b"test payload")

    rec = Recording(
        recording_id="rec_val_01",
        session_id="sess_01",
        signer_id="signer_01",
        source_video_sha256=correct_hash,
        storage_relative_path=rel_path,
        duration_ns=1_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
        status=RecordingStatus.INGESTED,
    )

    # Valid integrity check
    validate_recording_integrity(rec, storage_root)

    # Missing file raises QualityCheckError
    rec_missing = Recording(
        recording_id="rec_val_02",
        session_id="sess_01",
        signer_id="signer_01",
        source_video_sha256=correct_hash,
        storage_relative_path="objects/missing.mp4",
        duration_ns=1_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
    )
    with pytest.raises(QualityCheckError, match="Physical media file missing"):
        validate_recording_integrity(rec_missing, storage_root)

    # Empty file raises QualityCheckError
    empty_path = storage_root / "empty.mp4"
    empty_path.write_bytes(b"")
    rec_empty = Recording(
        recording_id="rec_val_03",
        session_id="sess_01",
        signer_id="signer_01",
        source_video_sha256=correct_hash,
        storage_relative_path="empty.mp4",
        duration_ns=1_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
    )
    with pytest.raises(QualityCheckError, match="empty"):
        validate_recording_integrity(rec_empty, storage_root)

    # Hash mismatch raises QualityCheckError
    rec_mismatch = Recording(
        recording_id="rec_val_04",
        session_id="sess_01",
        signer_id="signer_01",
        source_video_sha256="0" * 64,
        storage_relative_path=rel_path,
        duration_ns=1_000_000_000,
        fps_num=30,
        fps_den=1,
        width=1920,
        height=1080,
        container_format="mp4",
        video_codec="h264",
    )
    with pytest.raises(QualityCheckError, match="Checksum mismatch"):
        validate_recording_integrity(rec_mismatch, storage_root)


def test_annotation_tier_and_temporal_validation():
    allowed_tiers = {"sign_token", "translation_es"}
    ann1 = Annotation(
        annotation_id="a1",
        document_id="d1",
        tier_id="sign_token",
        start_ns=100,
        end_ns=500,
        value="HOLA",
    )
    ann2 = Annotation(
        annotation_id="a2",
        document_id="d1",
        tier_id="translation_es",
        start_ns=100,
        end_ns=500,
        value="hola",
    )
    # Valid tier checks
    validate_annotation_tiers([ann1, ann2], allowed_tiers)

    # Unregistered tier raises
    ann_bad_tier = Annotation(
        annotation_id="a3",
        document_id="d1",
        tier_id="unregistered_tier",
        start_ns=100,
        end_ns=500,
        value="test",
    )
    with pytest.raises(QualityCheckError, match="unregistered tier"):
        validate_annotation_tiers([ann_bad_tier], allowed_tiers)

    # Valid temporal bound check
    validate_annotation_temporal_bounds([ann1, ann2], max_duration_ns=1000)

    # Exceeding duration raises QualityCheckError
    with pytest.raises(QualityCheckError, match="exceeds recording duration"):
        validate_annotation_temporal_bounds([ann1], max_duration_ns=400)
