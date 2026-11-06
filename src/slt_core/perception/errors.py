"""SLT Perception Error Definitions."""
from __future__ import annotations

from slt_core.errors import SLTError


class PerceptionError(SLTError):
    """Base exception for visual perception."""


class InvalidFrameError(PerceptionError):
    """Invalid frame data or pixel format."""


class ModelAssetError(PerceptionError):
    """Missing, invalid or incompatible model asset."""


class PerceptionInitializationError(PerceptionError):
    """Unable to initialize a perception backend."""


class PerceptionProcessingError(PerceptionError):
    """A perception backend failed while processing a frame."""


class TrackingError(PerceptionError):
    """Invalid tracking state or temporal ordering."""


class GeometryError(PerceptionError):
    """Unable to calculate a geometric feature."""


class MotionError(PerceptionError):
    """Invalid temporal input for motion analysis."""


class CameraOpenError(PerceptionError):
    """Failed to open camera device."""


class CameraReadError(PerceptionError):
    """Failed to capture frame from camera."""


class VideoOpenError(PerceptionError):
    """Failed to open video file."""


class VideoDecodeError(PerceptionError):
    """Failed to decode frame from video."""


class InvalidVideoTimestampError(PerceptionError):
    """Invalid, missing or non-monotonic video presentation timestamp."""
