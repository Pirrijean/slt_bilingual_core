"""Unit tests for slt_corpus.storage content addressing and atomic ingestion."""

from __future__ import annotations

from pathlib import Path

import pytest

from slt_corpus.domain import ConsentPurpose, ConsentRecord
from slt_corpus.storage import StorageError, ingest_video

TEST_HASH = "c" * 64


def test_ingest_video_creates_content_addressed_file(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"synthetic-video-test-content-001")

    consent = ConsentRecord(
        consent_id="consent_001",
        signer_id="signer_001",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00+00:00",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    storage_root = tmp_path / "storage"

    result = ingest_video(
        source_path=source,
        storage_root=storage_root,
        consent=consent,
        signer_id="signer_001",
    )

    assert not result.is_duplicate
    assert result.absolute_path.is_file()
    assert result.relative_path.startswith("objects/sha256/")
    assert result.relative_path.endswith(".mp4")
    assert result.byte_size == len(b"synthetic-video-test-content-001")


def test_ingest_duplicate_video_detected(tmp_path: Path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"identical-video-bytes")

    consent = ConsentRecord(
        consent_id="consent_001",
        signer_id="signer_001",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00+00:00",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    storage_root = tmp_path / "storage"

    # Ingest first time
    res1 = ingest_video(
        source_path=source,
        storage_root=storage_root,
        consent=consent,
        signer_id="signer_001",
    )
    assert not res1.is_duplicate

    # Ingest second time
    res2 = ingest_video(
        source_path=source,
        storage_root=storage_root,
        consent=consent,
        signer_id="signer_001",
    )
    assert res2.is_duplicate
    assert res2.sha256 == res1.sha256


def test_unsupported_media_extension_rejected(tmp_path: Path):
    source = tmp_path / "dangerous.exe"
    source.write_bytes(b"not-a-video")

    consent = ConsentRecord(
        consent_id="consent_001",
        signer_id="signer_001",
        form_version="1.0.0",
        signed_at_utc="2026-11-06T10:00:00+00:00",
        granted_purposes=frozenset({ConsentPurpose.RECORD_AND_STORE}),
        evidence_sha256=TEST_HASH,
    )
    storage_root = tmp_path / "storage"

    with pytest.raises(StorageError, match="Unsupported video file extension"):
        ingest_video(
            source_path=source,
            storage_root=storage_root,
            consent=consent,
            signer_id="signer_001",
        )
