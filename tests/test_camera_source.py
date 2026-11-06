"""Unit tests for CameraSource using controlled test doubles."""
import numpy as np
import pytest

from slt_core.perception.errors import CameraOpenError, CameraReadError
from slt_core.sources.camera import CameraSource


class FakeCapture:
    def __init__(self, succeeds: bool = True):
        self.released = False
        self.succeeds = succeeds
        self.frames = [
            np.zeros((20, 30, 3), dtype=np.uint8),
            np.ones((20, 30, 3), dtype=np.uint8),
        ]

    def isOpened(self):
        return self.succeeds and not self.released

    def read(self):
        if not self.frames:
            return False, None
        return True, self.frames.pop(0)

    def release(self):
        self.released = True

    def set(self, prop, val):
        pass


def test_camera_source_lifecycle_and_reads():
    capture = FakeCapture()
    source = CameraSource(
        camera_index=0,
        capture_factory=lambda idx: capture,
        source_id="test_webcam",
    )

    assert source.ready is True
    assert source.source_id == "test_webcam"

    # Frame 0
    packet0 = source.read()
    assert packet0.source_id == "test_webcam"
    assert packet0.frame_index == 0
    assert packet0.timestamp_ns > 0
    assert packet0.image.shape == (20, 30, 3)

    # Frame 1
    packet1 = source.read()
    assert packet1.frame_index == 1
    assert packet1.timestamp_ns >= packet0.timestamp_ns

    # Empty buffer raises CameraReadError
    with pytest.raises(CameraReadError, match="Failed to read frame"):
        source.read()

    # Close releases hardware
    source.close()
    assert source.ready is False
    assert capture.released is True

    # Read when closed raises CameraReadError
    with pytest.raises(CameraReadError, match="not open"):
        source.read()


def test_camera_source_open_failure_raises():
    with pytest.raises(CameraOpenError):
        CameraSource(
            camera_index=99,
            capture_factory=lambda idx: FakeCapture(succeeds=False),
        )


def test_backend_candidates_discovery():
    from slt_core.sources.camera import _get_backend_candidates
    candidates = _get_backend_candidates()
    assert isinstance(candidates, list)
    assert len(candidates) >= 1
