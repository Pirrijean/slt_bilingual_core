"""Technical review service for video auditing and status adjudication."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from slt_corpus.catalog import CorpusCatalog
from slt_corpus.domain import RecordingStatus
from slt_corpus.media_probe import full_decode_audit


@dataclass(frozen=True, slots=True)
class TechnicalAuditResult:
    """Outcome of deep technical file verification."""

    recording_id: str
    file_exists: bool
    is_non_empty: bool
    size_bytes: int
    checksum_matches: bool
    calculated_sha256: str
    is_decodable: bool
    decoded_frames: int
    error_message: str | None = None


class ReviewService:
    """Encapsulates technical quality assessment and recording state progression."""

    def __init__(self, catalog: CorpusCatalog, storage_root: str | Path) -> None:
        self.catalog = catalog
        self.storage_root = Path(storage_root).resolve()

    def audit_recording(self, recording_id: str) -> TechnicalAuditResult:
        """Perform non-empty, checksum, container, and full decode audit of a recording."""
        rec = self.catalog.get_recording(recording_id)
        if rec is None:
            return TechnicalAuditResult(
                recording_id=recording_id,
                file_exists=False,
                is_non_empty=False,
                size_bytes=0,
                checksum_matches=False,
                calculated_sha256="",
                is_decodable=False,
                decoded_frames=0,
                error_message=f"Recording {recording_id!r} not found in catalog.",
            )

        file_path = self.storage_root / rec.storage_relative_path
        if not file_path.is_file():
            return TechnicalAuditResult(
                recording_id=recording_id,
                file_exists=False,
                is_non_empty=False,
                size_bytes=0,
                checksum_matches=False,
                calculated_sha256="",
                is_decodable=False,
                decoded_frames=0,
                error_message=f"Physical file missing at {file_path}",
            )

        size = file_path.stat().st_size
        if size == 0:
            return TechnicalAuditResult(
                recording_id=recording_id,
                file_exists=True,
                is_non_empty=False,
                size_bytes=0,
                checksum_matches=False,
                calculated_sha256="",
                is_decodable=False,
                decoded_frames=0,
                error_message="Physical file is empty (0 bytes).",
            )

        # Checksum calculation
        hasher = hashlib.sha256()
        with file_path.open("rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        calc_sha = hasher.hexdigest()
        matches = (calc_sha == rec.source_video_sha256)

        # PyAV Full decode audit
        try:
            decode_res = full_decode_audit(file_path)
            is_decodable = decode_res["status"] == "ok"
            decoded_frames = int(decode_res.get("frames_decoded", 0))
            err = decode_res.get("error")
        except Exception as exc:
            is_decodable = False
            decoded_frames = 0
            err = str(exc)

        return TechnicalAuditResult(
            recording_id=recording_id,
            file_exists=True,
            is_non_empty=True,
            size_bytes=size,
            checksum_matches=matches,
            calculated_sha256=calc_sha,
            is_decodable=is_decodable,
            decoded_frames=decoded_frames,
            error_message=err,
        )

    def advance_recording_status(self, recording_id: str, new_status: RecordingStatus) -> None:
        """Update recording status following technical or linguistic review."""
        self.catalog.update_recording_status(recording_id, new_status)
