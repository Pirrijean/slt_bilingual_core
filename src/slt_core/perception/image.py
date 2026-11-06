"""SLT Input Image Validation."""
from __future__ import annotations

import numpy as np

from slt_core.domain import FramePacket
from slt_core.perception.errors import InvalidFrameError


def validate_bgr_frame(packet: FramePacket) -> np.ndarray:
    """
    Validate that a FramePacket contains a well-formed BGR24 image matrix.
    Returns a contiguous uint8 HxWx3 ndarray.
    """
    if packet.pixel_format != "BGR24":
        raise InvalidFrameError(f"Expected BGR24 pixel format, got '{packet.pixel_format}'.")
    if packet.image is None:
        raise InvalidFrameError("FramePacket image cannot be None.")

    image = np.asarray(packet.image)
    if image.ndim != 3:
        raise InvalidFrameError(f"Image must have three dimensions: H x W x C, got {image.ndim} dimensions.")
    if image.shape[2] != 3:
        raise InvalidFrameError(f"Image must contain exactly 3 color channels, got {image.shape[2]}.")
    if image.shape[0] < 2 or image.shape[1] < 2:
        raise InvalidFrameError(f"Image dimensions must be at least 2x2, got {image.shape[0]}x{image.shape[1]}.")
    if image.dtype != np.uint8:
        raise InvalidFrameError(f"Image dtype must be uint8, got {image.dtype}.")

    return np.ascontiguousarray(image)
