"""Video capture recorder with integrity verification and automatic catalog ingestion."""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np

from slt_capture.session import CaptureSessionController
from slt_corpus.domain import Recording, RecordingStatus
from slt_corpus.storage import ingest_video


class RecorderError(Exception):
    """Raised when video recording or ingestion fails."""


class CaptureRecorder:
    """Manages writing video frames to disk and ingesting completed takes."""

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
        self._frame_count = 0
        self._start_monotonic_ns: int = 0
        self._end_monotonic_ns: int = 0
        self._width = 0
        self._height = 0
        self._target_fps = 30.0

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
        """Begin recording frames to an isolated temporary file."""
        if self._writer is not None:
            raise RecorderError("Recorder is already running.")

        # Re-check consent gating via session controller
        self.session.start_recording()

        self._width = width
        self._height = height
        self._target_fps = fps
        self._frame_count = 0
        self._start_monotonic_ns = time.monotonic_ns()

        self._current_temp_path = self.output_temp_dir / f"{recording_id}.raw.mp4"
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

    def write_frame(self, frame_bgr: np.ndarray) -> None:
        """Write a single BGR frame."""
        if self._writer is None:
            raise RecorderError("Cannot write frame: recorder is not running.")
        if frame_bgr.shape[0] != self._height or frame_bgr.shape[1] != self._width:
            raise RecorderError(
                f"Frame dimensions ({frame_bgr.shape[1]}x{frame_bgr.shape[0]}) "
                f"do not match recorder specification ({self._width}x{self._height})"
            )
        self._writer.write(frame_bgr)
        self._frame_count += 1

    def stop(self, recording_id: str) -> Recording:
        """Stop recording, release file, ingest into content-addressed storage, and register in catalog."""
        if self._writer is None or self._current_temp_path is None:
            raise RecorderError("Recorder is not running.")

        self._end_monotonic_ns = time.monotonic_ns()
        self._writer.release()
        self._writer = None
        self.session.stop_recording()

        duration_ns = max(1, self._end_monotonic_ns - self._start_monotonic_ns)

        if self._frame_count == 0 or not self._current_temp_path.is_file():
            if self._current_temp_path.exists():
                self._current_temp_path.unlink()
            raise RecorderError("No frames were recorded.")

        # Perform atomic ingestion into corpus storage
        consent = self.session._consent
        if consent is None:
            raise RecorderError("Missing session consent during ingestion.")

        stored_asset = ingest_video(
            source_path=self._current_temp_path,
            storage_root=self.storage_root,
            consent=consent,
            signer_id=self.session.signer_id,
        )

        # Remove local temporary file
        try:
            self._current_temp_path.unlink(missing_ok=True)
        except OSError:
            pass

        # Create Recording domain model
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
            metadata_json=f'{{"task_id": "{task_id}", "frames": {self._frame_count}}}',
        )

        self.session.catalog.add_recording(recording)
        return recording
