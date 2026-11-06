"""Video capture recorder with authoritative timestamp sidecars and automated ingestion."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np

from slt_capture.contracts import CaptureArtifact, CaptureFrameMetadata
from slt_capture.session import CaptureSessionController
from slt_corpus.domain import Recording, RecordingStatus
from slt_corpus.storage import ingest_video


class RecorderError(Exception):
    """Raised when video recording or ingestion fails."""


class CaptureRecorder:
    """Manages writing video frames to disk with authoritative timestamp sidecars."""

    def __init__(
        self,
        session_controller: CaptureSessionController,
        output_temp_dir: str | Path,
        storage_root: str | Path,
    ) -> None:
        self.session = session_controller
        self.output_temp_dir = Path(output_temp_dir).resolve()
        self.output_temp_dir.mkdir(parents=True, exist_ok=True)
        self.storage_root = Path(storage_root).resolve()

        self._writer: cv2.VideoWriter | None = None
        self._current_temp_path: Path | None = None
        self._current_sidecar_path: Path | None = None
        self._frame_metas: list[CaptureFrameMetadata] = []
        self._frame_count = 0
        self._start_monotonic_ns: int = 0
        self._end_monotonic_ns: int = 0
        self._width = 0
        self._height = 0
        self._target_fps = 30.0
        self.last_artifact: CaptureArtifact | None = None

    @property
    def is_recording(self) -> bool:
        return self._writer is not None

    def start(
        self,
        recording_id: str,
        width: int = 1920,
        height: int = 1080,
        fps: float = 30.0,
    ) -> None:
        """Begin recording frames to an isolated temporary file with a timestamp sidecar."""
        if self._writer is not None:
            raise RecorderError("Recorder is already running.")

        # Re-check consent gating via session controller
        self.session.start_recording()

        self._width = width
        self._height = height
        self._target_fps = fps
        self._frame_count = 0
        self._frame_metas = []
        self._start_monotonic_ns = time.monotonic_ns()

        self._current_temp_path = self.output_temp_dir / f"{recording_id}.raw.mp4"
        self._current_sidecar_path = self.output_temp_dir / f"{recording_id}.timestamps.json"

        fourcc = int(cv2.VideoWriter_fourcc(*"mp4v"))  # type: ignore[attr-defined]
        self._writer = cv2.VideoWriter(
            str(self._current_temp_path),
            fourcc,
            fps,
            (width, height),
        )
        if not self._writer.isOpened():
            self._writer = None
            raise RecorderError(f"Failed to open video writer for {self._current_temp_path}")

    def write_frame(
        self,
        frame_bgr: np.ndarray,
        capture_timestamp_ns: int | None = None,
    ) -> None:
        """Write a single BGR frame and record its authoritative capture timestamp."""
        if self._writer is None:
            raise RecorderError("Cannot write frame: recorder is not running.")
        if frame_bgr.shape[0] != self._height or frame_bgr.shape[1] != self._width:
            raise RecorderError(
                f"Frame dimensions ({frame_bgr.shape[1]}x{frame_bgr.shape[0]}) "
                f"do not match recorder specification ({self._width}x{self._height})"
            )

        ts_ns = capture_timestamp_ns if capture_timestamp_ns is not None else time.monotonic_ns()
        meta = CaptureFrameMetadata(
            frame_index=self._frame_count,
            capture_timestamp_ns=ts_ns,
            encoded_pts=self._frame_count,
            encoded_time_base_num=1,
            encoded_time_base_den=int(self._target_fps),
        )
        self._frame_metas.append(meta)

        self._writer.write(frame_bgr)
        self._frame_count += 1

    def stop(self, recording_id: str) -> Recording:
        """Stop recording, serialize sidecar, ingest into storage, and register in catalog."""
        if self._writer is None or self._current_temp_path is None or self._current_sidecar_path is None:
            raise RecorderError("Recorder is not running.")

        self._end_monotonic_ns = time.monotonic_ns()
        self._writer.release()
        self._writer = None
        self.session.stop_recording()

        duration_ns = max(1, self._end_monotonic_ns - self._start_monotonic_ns)

        if self._frame_count == 0 or not self._current_temp_path.is_file():
            if self._current_temp_path.exists():
                self._current_temp_path.unlink()
            if self._current_sidecar_path.exists():
                self._current_sidecar_path.unlink()
            raise RecorderError("No frames were recorded.")

        # Serialize authoritative timestamp sidecar
        sidecar_payload = {
            "recording_id": recording_id,
            "session_id": self.session.session_id,
            "signer_id": self.session.signer_id,
            "frame_count": self._frame_count,
            "target_fps": self._target_fps,
            "time_base": {"num": 1, "den": int(self._target_fps)},
            "frames": [
                {
                    "frame_index": f.frame_index,
                    "capture_timestamp_ns": f.capture_timestamp_ns,
                    "encoded_pts": f.encoded_pts,
                    "encoded_time_base_num": f.encoded_time_base_num,
                    "encoded_time_base_den": f.encoded_time_base_den,
                }
                for f in self._frame_metas
            ],
        }
        self._current_sidecar_path.write_text(json.dumps(sidecar_payload, indent=2), encoding="utf-8")

        # Compute media and sidecar SHA-256
        hasher_media = hashlib.sha256()
        with self._current_temp_path.open("rb") as f:
            while chunk := f.read(65536):
                hasher_media.update(chunk)
        media_sha256 = hasher_media.hexdigest()

        hasher_sidecar = hashlib.sha256()
        with self._current_sidecar_path.open("rb") as f:
            while chunk := f.read(65536):
                hasher_sidecar.update(chunk)
        sidecar_sha256 = hasher_sidecar.hexdigest()

        # Build CaptureArtifact
        self.last_artifact = CaptureArtifact(
            temporary_media_path=str(self._current_temp_path),
            timestamps_sidecar_path=str(self._current_sidecar_path),
            frame_count=self._frame_count,
            source_frame_timestamps_preserved=True,
            media_sha256=media_sha256,
            sidecar_sha256=sidecar_sha256,
        )

        # Ingest into content-addressed storage
        consent = self.session._consent
        if consent is None:
            raise RecorderError("Missing session consent during ingestion.")

        stored_asset = ingest_video(
            source_path=self._current_temp_path,
            storage_root=self.storage_root,
            consent=consent,
            signer_id=self.session.signer_id,
        )

        # Remove local temporary media
        try:
            self._current_temp_path.unlink(missing_ok=True)
        except OSError:
            pass

        task_id = self.session.active_task.task_id if self.session.active_task else "general"
        recording = Recording(
            recording_id=recording_id,
            session_id=self.session.session_id,
            signer_id=self.session.signer_id,
            source_video_sha256=stored_asset.sha256,
            storage_relative_path=stored_asset.relative_path,
            duration_ns=duration_ns,
            fps_num=int(self._target_fps),
            fps_den=1,
            width=self._width,
            height=self._height,
            container_format="mp4",
            video_codec="h264",
            status=RecordingStatus.INGESTED,
            metadata_json=json.dumps({
                "task_id": task_id,
                "frames": self._frame_count,
                "sidecar_sha256": sidecar_sha256,
                "source_timestamps_preserved": True,
            }),
        )

        self.session.catalog.add_recording(recording)
        return recording
