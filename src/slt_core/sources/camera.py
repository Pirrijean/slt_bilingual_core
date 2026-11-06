"""Cross-platform Camera FrameSource for SLT Core."""
from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable
from typing import Any

import cv2

from slt_core.domain import FramePacket
from slt_core.perception.errors import CameraOpenError, CameraReadError
from slt_core.perception.image import validate_bgr_frame


def _get_backend_candidates() -> list[int]:
    """Return prioritized OpenCV capture backends for the current operating system."""
    candidates: list[int] = []
    if os.name == "nt":  # Windows
        if hasattr(cv2, "CAP_DSHOW"):
            candidates.append(cv2.CAP_DSHOW)
        if hasattr(cv2, "CAP_MSMF"):
            candidates.append(cv2.CAP_MSMF)
    elif sys.platform == "darwin":  # macOS
        if hasattr(cv2, "CAP_AVFOUNDATION"):
            candidates.append(cv2.CAP_AVFOUNDATION)
    else:  # Linux / Unix
        if hasattr(cv2, "CAP_V4L2"):
            candidates.append(cv2.CAP_V4L2)

    candidates.append(cv2.CAP_ANY)
    return candidates


class CameraSource:
    """
    Captures live frames from a physical or virtual camera device.
    Assigns monotonic timestamps and validates BGR24 formatting.
    """

    def __init__(
        self,
        camera_index: int = 0,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        source_id: str | None = None,
        capture_factory: Callable[..., Any] | None = None,
    ) -> None:
        self.camera_index = camera_index
        self._source_id = source_id or f"camera_{camera_index}"
        self._width = width
        self._height = height
        self._fps = fps
        self._frame_index = 0
        self._cap: Any | None = None
        self._is_open = False

        self._open(capture_factory)

    def _open(self, capture_factory: Callable[..., Any] | None = None) -> None:
        if capture_factory is not None:
            self._cap = capture_factory(self.camera_index)
            if not self._cap.isOpened():
                raise CameraOpenError(f"Custom capture factory failed to open index {self.camera_index}.")
            self._is_open = True
            return

        candidates = _get_backend_candidates()
        opened_cap: Any | None = None

        for backend in candidates:
            try:
                cap = cv2.VideoCapture(self.camera_index, backend)
                if cap.isOpened():
                    opened_cap = cap
                    break
                cap.release()
            except Exception:  # noqa: BLE001, S112
                continue

        if opened_cap is None:
            raise CameraOpenError(
                f"Unable to open camera at index {self.camera_index} with any available system backend."
            )

        self._cap = opened_cap
        # Configure requested parameters as best-effort
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._height)
        self._cap.set(cv2.CAP_PROP_FPS, self._fps)
        if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        self._is_open = True

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def ready(self) -> bool:
        return self._is_open and self._cap is not None and bool(self._cap.isOpened())

    def read(self) -> FramePacket:
        """
        Capture and return the next frame packet.
        Raises CameraReadError if the camera fails or disconnects.
        """
        if not self.ready or self._cap is None:
            raise CameraReadError("Camera is not open or available.")

        ret, frame = self._cap.read()
        if not ret or frame is None:
            raise CameraReadError(f"Failed to read frame {self._frame_index} from camera.")

        timestamp_ns = time.monotonic_ns()

        packet = FramePacket(
            source_id=self._source_id,
            frame_index=self._frame_index,
            timestamp_ns=timestamp_ns,
            image=frame,
            pixel_format="BGR24",
            timestamp_kind="monotonic",
        )
        validated_image = validate_bgr_frame(packet)

        current_index = self._frame_index
        self._frame_index += 1

        return FramePacket(
            source_id=packet.source_id,
            frame_index=current_index,
            timestamp_ns=packet.timestamp_ns,
            image=validated_image,
            pixel_format=packet.pixel_format,
            timestamp_kind=packet.timestamp_kind,
        )

    def close(self) -> None:
        """Release camera hardware resources idempotently."""
        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:  # noqa: BLE001, S110
                pass
            self._cap = None
        self._is_open = False
