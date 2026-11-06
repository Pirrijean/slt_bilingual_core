"""Relational catalog using SQLite with strict integrity, transactions, and FKs."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

from slt_corpus.domain import (
    Annotation,
    AnnotationDocument,
    AnnotationStatus,
    Asset,
    BoundaryQuality,
    ConsentPurpose,
    ConsentRecord,
    DatasetRelease,
    Participant,
    Recording,
    RecordingStatus,
    ReleaseApprovalStatus,
    Session,
    SplitAssignment,
)

SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS participants (
    signer_id TEXT PRIMARY KEY,
    metadata_json TEXT NOT NULL,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consents (
    consent_id TEXT PRIMARY KEY,
    signer_id TEXT NOT NULL REFERENCES participants(signer_id) ON DELETE RESTRICT,
    form_version TEXT NOT NULL,
    signed_at_utc TEXT NOT NULL,
    granted_purposes_json TEXT NOT NULL,
    evidence_sha256 TEXT NOT NULL,
    revoked_at_utc TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    signer_id TEXT NOT NULL REFERENCES participants(signer_id) ON DELETE RESTRICT,
    protocol_id TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL,
    operator_id TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recordings (
    recording_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE RESTRICT,
    signer_id TEXT NOT NULL REFERENCES participants(signer_id) ON DELETE RESTRICT,
    source_video_sha256 TEXT NOT NULL,
    storage_relative_path TEXT NOT NULL,
    duration_ns INTEGER NOT NULL,
    fps_num INTEGER,
    fps_den INTEGER,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    container_format TEXT NOT NULL,
    video_codec TEXT NOT NULL,
    status TEXT NOT NULL,
    parent_recording_id TEXT REFERENCES recordings(recording_id),
    metadata_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    parent_recording_id TEXT NOT NULL REFERENCES recordings(recording_id) ON DELETE RESTRICT,
    asset_type TEXT NOT NULL,
    storage_relative_path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    extractor_name TEXT,
    extractor_version TEXT,
    model_sha256 TEXT,
    configuration_hash TEXT,
    created_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotation_documents (
    document_id TEXT PRIMARY KEY,
    recording_id TEXT NOT NULL REFERENCES recordings(recording_id) ON DELETE RESTRICT,
    schema_version TEXT NOT NULL,
    eaf_source_path TEXT,
    created_at_utc TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotations (
    annotation_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES annotation_documents(document_id) ON DELETE CASCADE,
    tier_id TEXT NOT NULL,
    start_ns INTEGER NOT NULL,
    end_ns INTEGER NOT NULL,
    value TEXT NOT NULL,
    parent_annotation_id TEXT REFERENCES annotations(annotation_id),
    boundary_quality TEXT NOT NULL,
    status TEXT NOT NULL,
    annotator_id TEXT,
    revision INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS annotation_reviews (
    review_id TEXT PRIMARY KEY,
    annotation_id TEXT NOT NULL REFERENCES annotations(annotation_id) ON DELETE CASCADE,
    reviewer_id TEXT NOT NULL,
    status TEXT NOT NULL,
    comments TEXT NOT NULL,
    reviewed_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_releases (
    release_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    profile_id TEXT NOT NULL,
    task TEXT NOT NULL,
    created_at_utc TEXT NOT NULL,
    corpus_version TEXT NOT NULL,
    annotation_schema_version TEXT NOT NULL,
    usage_scope TEXT NOT NULL,
    split_manifest_relpath TEXT NOT NULL,
    approval_status TEXT NOT NULL,
    source_recording_ids_json TEXT NOT NULL,
    annotation_document_ids_json TEXT NOT NULL,
    license_review_status TEXT NOT NULL,
    parent_release_id TEXT REFERENCES dataset_releases(release_id),
    code_commit TEXT
);

CREATE TABLE IF NOT EXISTS split_assignments (
    split_id TEXT PRIMARY KEY,
    dataset_release_id TEXT NOT NULL REFERENCES dataset_releases(release_id) ON DELETE CASCADE,
    split_name TEXT NOT NULL,
    recording_id TEXT NOT NULL REFERENCES recordings(recording_id) ON DELETE RESTRICT,
    signer_id TEXT NOT NULL REFERENCES participants(signer_id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_recordings_signer ON recordings(signer_id);
CREATE INDEX IF NOT EXISTS idx_recordings_session ON recordings(session_id);
CREATE INDEX IF NOT EXISTS idx_annotations_doc ON annotations(document_id);
CREATE INDEX IF NOT EXISTS idx_annotations_tier ON annotations(tier_id);
CREATE INDEX IF NOT EXISTS idx_splits_release ON split_assignments(dataset_release_id);
"""


class CorpusCatalog:
    """Relational SQLite repository for SLT corpus entities."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA_DDL)

    # -------------------------------------------------------------------------
    # Participants
    # -------------------------------------------------------------------------
    def add_participant(self, participant: Participant) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO participants (signer_id, metadata_json, created_at_utc)
                VALUES (?, ?, ?)
                """,
                (participant.signer_id, participant.metadata_json, participant.created_at_utc),
            )

    def get_participant(self, signer_id: str) -> Participant | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT signer_id, metadata_json, created_at_utc FROM participants WHERE signer_id = ?",
                (signer_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return Participant(
                signer_id=row["signer_id"],
                metadata_json=row["metadata_json"],
                created_at_utc=row["created_at_utc"],
            )

    def list_participants(self) -> list[Participant]:
        with self._connect() as conn:
            cur = conn.execute("SELECT signer_id, metadata_json, created_at_utc FROM participants ORDER BY signer_id")
            return [
                Participant(
                    signer_id=r["signer_id"],
                    metadata_json=r["metadata_json"],
                    created_at_utc=r["created_at_utc"],
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------------------
    # Consents
    # -------------------------------------------------------------------------
    def add_consent(self, consent: ConsentRecord) -> None:
        purposes_json = json.dumps([p.value for p in consent.granted_purposes])
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO consents (
                    consent_id, signer_id, form_version, signed_at_utc,
                    granted_purposes_json, evidence_sha256, revoked_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    consent.consent_id,
                    consent.signer_id,
                    consent.form_version,
                    consent.signed_at_utc,
                    purposes_json,
                    consent.evidence_sha256,
                    consent.revoked_at_utc,
                ),
            )

    def get_consent(self, consent_id: str) -> ConsentRecord | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT consent_id, signer_id, form_version, signed_at_utc,
                       granted_purposes_json, evidence_sha256, revoked_at_utc
                FROM consents WHERE consent_id = ?
                """,
                (consent_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            purposes = frozenset(ConsentPurpose(p) for p in json.loads(row["granted_purposes_json"]))
            return ConsentRecord(
                consent_id=row["consent_id"],
                signer_id=row["signer_id"],
                form_version=row["form_version"],
                signed_at_utc=row["signed_at_utc"],
                granted_purposes=purposes,
                evidence_sha256=row["evidence_sha256"],
                revoked_at_utc=row["revoked_at_utc"],
            )

    def get_latest_consent_for_signer(self, signer_id: str) -> ConsentRecord | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT consent_id, signer_id, form_version, signed_at_utc,
                       granted_purposes_json, evidence_sha256, revoked_at_utc
                FROM consents
                WHERE signer_id = ?
                ORDER BY signed_at_utc DESC
                LIMIT 1
                """,
                (signer_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            purposes = frozenset(ConsentPurpose(p) for p in json.loads(row["granted_purposes_json"]))
            return ConsentRecord(
                consent_id=row["consent_id"],
                signer_id=row["signer_id"],
                form_version=row["form_version"],
                signed_at_utc=row["signed_at_utc"],
                granted_purposes=purposes,
                evidence_sha256=row["evidence_sha256"],
                revoked_at_utc=row["revoked_at_utc"],
            )

    def revoke_consent(self, consent_id: str, revoked_at_utc: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE consents SET revoked_at_utc = ? WHERE consent_id = ?",
                (revoked_at_utc, consent_id),
            )

    # -------------------------------------------------------------------------
    # Sessions
    # -------------------------------------------------------------------------
    def add_session(self, session: Session) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, signer_id, protocol_id, recorded_at_utc,
                    operator_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_id,
                    session.signer_id,
                    session.protocol_id,
                    session.recorded_at_utc,
                    session.operator_id,
                    session.metadata_json,
                ),
            )

    def get_session(self, session_id: str) -> Session | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT session_id, signer_id, protocol_id, recorded_at_utc,
                       operator_id, metadata_json
                FROM sessions WHERE session_id = ?
                """,
                (session_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return Session(
                session_id=row["session_id"],
                signer_id=row["signer_id"],
                protocol_id=row["protocol_id"],
                recorded_at_utc=row["recorded_at_utc"],
                operator_id=row["operator_id"],
                metadata_json=row["metadata_json"],
            )

    # -------------------------------------------------------------------------
    # Recordings
    # -------------------------------------------------------------------------
    def add_recording(self, recording: Recording) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO recordings (
                    recording_id, session_id, signer_id, source_video_sha256,
                    storage_relative_path, duration_ns, fps_num, fps_den,
                    width, height, container_format, video_codec,
                    status, parent_recording_id, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    recording.recording_id,
                    recording.session_id,
                    recording.signer_id,
                    recording.source_video_sha256,
                    recording.storage_relative_path,
                    recording.duration_ns,
                    recording.fps_num,
                    recording.fps_den,
                    recording.width,
                    recording.height,
                    recording.container_format,
                    recording.video_codec,
                    recording.status.value,
                    recording.parent_recording_id,
                    recording.metadata_json,
                ),
            )

    def get_recording(self, recording_id: str) -> Recording | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT recording_id, session_id, signer_id, source_video_sha256,
                       storage_relative_path, duration_ns, fps_num, fps_den,
                       width, height, container_format, video_codec,
                       status, parent_recording_id, metadata_json
                FROM recordings WHERE recording_id = ?
                """,
                (recording_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return self._row_to_recording(row)

    def list_recordings(self) -> list[Recording]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT recording_id, session_id, signer_id, source_video_sha256,
                       storage_relative_path, duration_ns, fps_num, fps_den,
                       width, height, container_format, video_codec,
                       status, parent_recording_id, metadata_json
                FROM recordings ORDER BY recording_id
                """
            )
            return [self._row_to_recording(r) for r in cur.fetchall()]

    @staticmethod
    def _row_to_recording(row: sqlite3.Row) -> Recording:
        return Recording(
            recording_id=row["recording_id"],
            session_id=row["session_id"],
            signer_id=row["signer_id"],
            source_video_sha256=row["source_video_sha256"],
            storage_relative_path=row["storage_relative_path"],
            duration_ns=row["duration_ns"],
            fps_num=row["fps_num"],
            fps_den=row["fps_den"],
            width=row["width"],
            height=row["height"],
            container_format=row["container_format"],
            video_codec=row["video_codec"],
            status=RecordingStatus(row["status"]),
            parent_recording_id=row["parent_recording_id"],
            metadata_json=row["metadata_json"],
        )

    # -------------------------------------------------------------------------
    # Assets
    # -------------------------------------------------------------------------
    def add_asset(self, asset: Asset) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assets (
                    asset_id, parent_recording_id, asset_type,
                    storage_relative_path, sha256, extractor_name,
                    extractor_version, model_sha256, configuration_hash,
                    created_at_utc
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    asset.asset_id,
                    asset.parent_recording_id,
                    asset.asset_type,
                    asset.storage_relative_path,
                    asset.sha256,
                    asset.extractor_name,
                    asset.extractor_version,
                    asset.model_sha256,
                    asset.configuration_hash,
                    asset.created_at_utc,
                ),
            )

    def get_asset(self, asset_id: str) -> Asset | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT asset_id, parent_recording_id, asset_type,
                       storage_relative_path, sha256, extractor_name,
                       extractor_version, model_sha256, configuration_hash,
                       created_at_utc
                FROM assets WHERE asset_id = ?
                """,
                (asset_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return Asset(
                asset_id=row["asset_id"],
                parent_recording_id=row["parent_recording_id"],
                asset_type=row["asset_type"],
                storage_relative_path=row["storage_relative_path"],
                sha256=row["sha256"],
                extractor_name=row["extractor_name"],
                extractor_version=row["extractor_version"],
                model_sha256=row["model_sha256"],
                configuration_hash=row["configuration_hash"],
                created_at_utc=row["created_at_utc"],
            )

    # -------------------------------------------------------------------------
    # Annotations
    # -------------------------------------------------------------------------
    def add_annotation_document(self, doc: AnnotationDocument) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO annotation_documents (
                    document_id, recording_id, schema_version,
                    eaf_source_path, created_at_utc, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    doc.document_id,
                    doc.recording_id,
                    doc.schema_version,
                    doc.eaf_source_path,
                    doc.created_at_utc,
                    doc.status.value,
                ),
            )

    def add_annotations(self, annotations: Sequence[Annotation]) -> None:
        with self._connect() as conn:
            for ann in annotations:
                conn.execute(
                    """
                    INSERT INTO annotations (
                        annotation_id, document_id, tier_id, start_ns, end_ns,
                        value, parent_annotation_id, boundary_quality, status,
                        annotator_id, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ann.annotation_id,
                        ann.document_id,
                        ann.tier_id,
                        ann.start_ns,
                        ann.end_ns,
                        ann.value,
                        ann.parent_annotation_id,
                        ann.boundary_quality.value,
                        ann.status.value,
                        ann.annotator_id,
                        ann.revision,
                    ),
                )

    def get_annotations_for_document(self, document_id: str) -> list[Annotation]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT annotation_id, document_id, tier_id, start_ns, end_ns,
                       value, parent_annotation_id, boundary_quality, status,
                       annotator_id, revision
                FROM annotations
                WHERE document_id = ?
                ORDER BY start_ns, tier_id
                """,
                (document_id,),
            )
            return [
                Annotation(
                    annotation_id=r["annotation_id"],
                    document_id=r["document_id"],
                    tier_id=r["tier_id"],
                    start_ns=r["start_ns"],
                    end_ns=r["end_ns"],
                    value=r["value"],
                    parent_annotation_id=r["parent_annotation_id"],
                    boundary_quality=BoundaryQuality(r["boundary_quality"]),
                    status=AnnotationStatus(r["status"]),
                    annotator_id=r["annotator_id"],
                    revision=r["revision"],
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------------------
    # Dataset Releases and Splits
    # -------------------------------------------------------------------------
    def add_dataset_release(
        self, release: DatasetRelease, splits: Sequence[SplitAssignment]
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO dataset_releases (
                    release_id, dataset_id, dataset_version, profile_id,
                    task, created_at_utc, corpus_version,
                    annotation_schema_version, usage_scope, split_manifest_relpath,
                    approval_status, source_recording_ids_json,
                    annotation_document_ids_json, license_review_status,
                    parent_release_id, code_commit
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    release.release_id,
                    release.dataset_id,
                    release.dataset_version,
                    release.profile_id,
                    release.task,
                    release.created_at_utc,
                    release.corpus_version,
                    release.annotation_schema_version,
                    release.usage_scope.value,
                    release.split_manifest_relpath,
                    release.approval_status.value,
                    json.dumps(list(release.source_recording_ids)),
                    json.dumps(list(release.annotation_document_ids)),
                    release.license_review_status,
                    release.parent_release_id,
                    release.code_commit,
                ),
            )
            for sp in splits:
                conn.execute(
                    """
                    INSERT INTO split_assignments (
                        split_id, dataset_release_id, split_name,
                        recording_id, signer_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        sp.split_id,
                        sp.dataset_release_id,
                        sp.split_name,
                        sp.recording_id,
                        sp.signer_id,
                    ),
                )

    def get_dataset_release(self, release_id: str) -> DatasetRelease | None:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT release_id, dataset_id, dataset_version, profile_id,
                       task, created_at_utc, corpus_version,
                       annotation_schema_version, usage_scope, split_manifest_relpath,
                       approval_status, source_recording_ids_json,
                       annotation_document_ids_json, license_review_status,
                       parent_release_id, code_commit
                FROM dataset_releases WHERE release_id = ?
                """,
                (release_id,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return DatasetRelease(
                release_id=row["release_id"],
                dataset_id=row["dataset_id"],
                dataset_version=row["dataset_version"],
                profile_id=row["profile_id"],
                task=row["task"],
                created_at_utc=row["created_at_utc"],
                corpus_version=row["corpus_version"],
                annotation_schema_version=row["annotation_schema_version"],
                usage_scope=ConsentPurpose(row["usage_scope"]),
                split_manifest_relpath=row["split_manifest_relpath"],
                approval_status=ReleaseApprovalStatus(row["approval_status"]),
                source_recording_ids=tuple(json.loads(row["source_recording_ids_json"])),
                annotation_document_ids=tuple(json.loads(row["annotation_document_ids_json"])),
                license_review_status=row["license_review_status"],
                parent_release_id=row["parent_release_id"],
                code_commit=row["code_commit"],
            )

    def get_split_assignments(self, release_id: str) -> list[SplitAssignment]:
        with self._connect() as conn:
            cur = conn.execute(
                """
                SELECT split_id, dataset_release_id, split_name, recording_id, signer_id
                FROM split_assignments
                WHERE dataset_release_id = ?
                ORDER BY split_name, recording_id
                """,
                (release_id,),
            )
            return [
                SplitAssignment(
                    split_id=r["split_id"],
                    dataset_release_id=r["dataset_release_id"],
                    split_name=r["split_name"],
                    recording_id=r["recording_id"],
                    signer_id=r["signer_id"],
                )
                for r in cur.fetchall()
            ]

    # -------------------------------------------------------------------------
    # Backup
    # -------------------------------------------------------------------------
    def create_backup(self, backup_path: str | Path) -> None:
        """Create an atomic, consistent backup of the SQLite database."""
        dest = Path(backup_path).resolve()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as src_conn, sqlite3.connect(str(dest)) as dst_conn:
            src_conn.backup(dst_conn)
