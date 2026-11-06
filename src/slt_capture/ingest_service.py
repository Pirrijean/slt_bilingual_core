"""Ingestion service connecting capture artifacts to content-addressed storage and catalog."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from slt_capture.contracts import CaptureArtifact
from slt_corpus.catalog import CorpusCatalog
from slt_corpus.consent import validate_video_storage_scope
from slt_corpus.domain import (
    ConsentRecord,
    Recording,
    RecordingStatus,
)
from slt_corpus.storage import ingest_video


class IngestError(Exception):
    """Raised when an ingestion validation or storage operation fails."""


class CaptureIngestService:
    """Orchestrates intake of capture artifacts into immutable storage and the SQLite catalog."""

    def __init__(self, catalog: CorpusCatalog, storage_root: str | Path) -> None:
        self.catalog = catalog
        self.storage_root = Path(storage_root).resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def ingest_capture_artifact(
        self,
        artifact: CaptureArtifact,
        recording_id: str,
        session_id: str,
        signer_id: str,
        consent: ConsentRecord,
        width: int,
        height: int,
        fps_num: int = 30,
        fps_den: int = 1,
        container_format: str = "mp4",
        video_codec: str = "h264",
        extra_metadata: dict[str, object] | None = None,
    ) -> Recording:
        """Validate artifact integrity, verify consent, store files, and register catalog record."""
        # 1. Verify consent
        validate_video_storage_scope(consent, signer_id)

        media_path = Path(artifact.temporary_media_path)
        sidecar_path = Path(artifact.timestamps_sidecar_path)

        if not media_path.is_file():
            raise IngestError(f"Media file not found at {media_path}")
        if not sidecar_path.is_file():
            raise IngestError(f"Timestamp sidecar file not found at {sidecar_path}")

        # 2. Checksum verification
        hasher_media = hashlib.sha256()
        with media_path.open("rb") as f:
            while chunk := f.read(65536):
                hasher_media.update(chunk)
        calc_media_sha256 = hasher_media.hexdigest()

        if calc_media_sha256 != artifact.media_sha256:
            raise IngestError(
                f"Media checksum mismatch. Expected {artifact.media_sha256}, calculated {calc_media_sha256}"
            )

        hasher_sidecar = hashlib.sha256()
        with sidecar_path.open("rb") as f:
            while chunk := f.read(65536):
                hasher_sidecar.update(chunk)
        calc_sidecar_sha256 = hasher_sidecar.hexdigest()

        if calc_sidecar_sha256 != artifact.sidecar_sha256:
            raise IngestError(
                f"Sidecar checksum mismatch. Expected {artifact.sidecar_sha256}, calculated {calc_sidecar_sha256}"
            )

        # 3. Store video in Content Addressed Storage
        stored_video = ingest_video(
            source_path=media_path,
            storage_root=self.storage_root,
            consent=consent,
            signer_id=signer_id,
        )

        # 4. Read sidecar to calculate duration and timing details
        try:
            sidecar_data = json.loads(sidecar_path.read_text(encoding="utf-8"))
            frames_meta = sidecar_data.get("frames", [])
            if frames_meta:
                start_ns = frames_meta[0]["capture_timestamp_ns"]
                end_ns = frames_meta[-1]["capture_timestamp_ns"]
                duration_ns = max(1, end_ns - start_ns)
            else:
                duration_ns = max(1, int((artifact.frame_count / max(1, fps_num)) * 1_000_000_000))
        except (json.JSONDecodeError, KeyError, IndexError):
            duration_ns = max(1, int((artifact.frame_count / max(1, fps_num)) * 1_000_000_000))

        # 5. Prepare recording metadata JSON
        meta_dict: dict[str, object] = {
            "sidecar_sha256": artifact.sidecar_sha256,
            "frame_count": artifact.frame_count,
            "source_timestamps_preserved": artifact.source_frame_timestamps_preserved,
        }
        if extra_metadata:
            meta_dict.update(extra_metadata)

        recording = Recording(
            recording_id=recording_id,
            session_id=session_id,
            signer_id=signer_id,
            source_video_sha256=stored_video.sha256,
            storage_relative_path=stored_video.relative_path,
            duration_ns=duration_ns,
            fps_num=fps_num,
            fps_den=fps_den,
            width=width,
            height=height,
            container_format=container_format,
            video_codec=video_codec,
            status=RecordingStatus.INGESTED,
            metadata_json=json.dumps(meta_dict),
        )

        self.catalog.add_recording(recording)
        return recording
