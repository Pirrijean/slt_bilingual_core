"""Unit tests for slt_corpus.release manifest building and gating."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import (
    ConsentPurpose,
    ConsentRecord,
    Participant,
    Recording,
    Session,
)
from slt_corpus.release import DatasetReleaseManager, ReleaseError

TEST_HASH = "e" * 64


def test_build_release_success(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    storage_root = tmp_path / "storage"
    catalog = CorpusCatalog(db_path)

    # 1. Register participants and consents
    for s_id in ("signer_A", "signer_B"):
        catalog.add_participant(
            Participant(signer_id=s_id, metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
        )
        catalog.add_consent(
            ConsentRecord(
                consent_id=f"c_{s_id}",
                signer_id=s_id,
                form_version="1.0.0",
                signed_at_utc="2026-11-06T10:00:00Z",
                granted_purposes=frozenset({ConsentPurpose.INTERNAL_RESEARCH}),
                evidence_sha256=TEST_HASH,
            )
        )

    # 2. Register session and recordings
    catalog.add_session(
        Session(
            session_id="sess_01",
            signer_id="signer_A",
            protocol_id="continuous_v1",
            recorded_at_utc="2026-11-06T10:00:00Z",
            operator_id="op_01",
        )
    )
    catalog.add_session(
        Session(
            session_id="sess_02",
            signer_id="signer_B",
            protocol_id="continuous_v1",
            recorded_at_utc="2026-11-06T10:00:00Z",
            operator_id="op_01",
        )
    )

    catalog.add_recording(
        Recording(
            recording_id="rec_A1",
            session_id="sess_01",
            signer_id="signer_A",
            source_video_sha256=TEST_HASH,
            storage_relative_path="objects/sha256/ee/rec_A1.mp4",
            duration_ns=1_000_000_000,
            fps_num=30,
            fps_den=1,
            width=1920,
            height=1080,
            container_format="mp4",
            video_codec="h264",
        )
    )
    catalog.add_recording(
        Recording(
            recording_id="rec_B1",
            session_id="sess_02",
            signer_id="signer_B",
            source_video_sha256=TEST_HASH,
            storage_relative_path="objects/sha256/ee/rec_B1.mp4",
            duration_ns=1_000_000_000,
            fps_num=30,
            fps_den=1,
            width=1920,
            height=1080,
            container_format="mp4",
            video_codec="h264",
        )
    )

    manager = DatasetReleaseManager(catalog, storage_root)
    out_dir = tmp_path / "releases" / "lsc_continuous_0_1_0"

    release = manager.build_release(
        dataset_id="lsc-continuous",
        dataset_version="0.1.0",
        profile_id="lsc",
        task="continuous_sign_recognition",
        corpus_version="0.1.0",
        annotation_schema_version="1.0.0",
        usage_scope=ConsentPurpose.INTERNAL_RESEARCH,
        split_members={"train": ["rec_A1"], "test": ["rec_B1"]},
        output_dir=out_dir,
    )

    assert release.release_id == "lsc_continuous_0_1_0"
    assert (out_dir / "dataset_release.json").is_file()
    assert (out_dir / "splits.json").is_file()

    # Re-read manifest
    manifest_data = json.loads((out_dir / "dataset_release.json").read_text(encoding="utf-8"))
    assert manifest_data["dataset_id"] == "lsc-continuous"


def test_build_release_commercial_scope_denied_without_commercial_consent(tmp_path: Path):
    db_path = tmp_path / "catalog.sqlite3"
    storage_root = tmp_path / "storage"
    catalog = CorpusCatalog(db_path)

    catalog.add_participant(
        Participant(signer_id="signer_res", metadata_json="{}", created_at_utc="2026-11-06T10:00:00Z")
    )
    # Grant ONLY internal research
    catalog.add_consent(
        ConsentRecord(
            consent_id="c_res",
            signer_id="signer_res",
            form_version="1.0.0",
            signed_at_utc="2026-11-06T10:00:00Z",
            granted_purposes=frozenset({ConsentPurpose.INTERNAL_RESEARCH}),
            evidence_sha256=TEST_HASH,
        )
    )
    catalog.add_session(
        Session(
            session_id="s_res",
            signer_id="signer_res",
            protocol_id="continuous_v1",
            recorded_at_utc="2026-11-06T10:00:00Z",
            operator_id="op_01",
        )
    )
    catalog.add_recording(
        Recording(
            recording_id="rec_res",
            session_id="s_res",
            signer_id="signer_res",
            source_video_sha256=TEST_HASH,
            storage_relative_path="objects/sha256/ee/rec.mp4",
            duration_ns=1_000_000_000,
            fps_num=30,
            fps_den=1,
            width=1920,
            height=1080,
            container_format="mp4",
            video_codec="h264",
        )
    )

    manager = DatasetReleaseManager(catalog, storage_root)
    out_dir = tmp_path / "releases" / "commercial_try"

    # Attempting COMMERCIAL_TRAINING release must raise ReleaseError
    with pytest.raises(ReleaseError, match="Consent gating failed"):
        manager.build_release(
            dataset_id="lsc-continuous",
            dataset_version="0.1.0",
            profile_id="lsc",
            task="continuous_sign_recognition",
            corpus_version="0.1.0",
            annotation_schema_version="1.0.0",
            usage_scope=ConsentPurpose.COMMERCIAL_TRAINING,
            split_members={"train": ["rec_res"]},
            output_dir=out_dir,
        )
