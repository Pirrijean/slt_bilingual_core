"""Video container and stream probe using PyAV."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import av


class MediaProbeError(Exception):
    """Raised when media inspection or decoding fails."""


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Technical stream metadata extracted from container."""

    media_type: str
    width: int
    height: int
    duration_ns: int | None
    frame_rate_num: int | None
    frame_rate_den: int | None
    time_base_num: int | None
    time_base_den: int | None


def probe_video(path: str | Path) -> VideoMetadata:
    """Inspect the first decodable video stream in a media container.

    Raises:
        MediaProbeError: If file does not exist, container is invalid, or no video stream exists.
    """
    target = Path(path).resolve()
    if not target.is_file():
        raise MediaProbeError(f"Video file does not exist at: {target}")

    try:
        container = av.open(str(target))
    except Exception as exc:
        raise MediaProbeError(f"Failed to open media container {target}: {exc}") from exc

    try:
        video_streams = container.streams.video
        if not video_streams:
            raise MediaProbeError(f"No video streams found in: {target}")

        stream = video_streams[0]
        width = int(stream.width)
        height = int(stream.height)
        if width <= 0 or height <= 0:
            raise MediaProbeError(f"Invalid video dimensions: {width}x{height}")

        # Frame rate
        fps_num: int | None = None
        fps_den: int | None = None
        if stream.average_rate is not None:
            fps_num = int(stream.average_rate.numerator)
            fps_den = int(stream.average_rate.denominator)

        # Time base
        tb_num: int | None = None
        tb_den: int | None = None
        if stream.time_base is not None:
            tb_num = int(stream.time_base.numerator)
            tb_den = int(stream.time_base.denominator)

        # Duration
        duration_ns: int | None = None
        if stream.duration is not None and stream.time_base is not None:
            dur_sec = float(stream.duration * stream.time_base)
            if dur_sec >= 0:
                duration_ns = int(dur_sec * 1_000_000_000)
        elif container.duration is not None:
            dur_sec = float(container.duration / av.time_base)
            if dur_sec >= 0:
                duration_ns = int(dur_sec * 1_000_000_000)

        # Verify first frame can be decoded
        first_frame_found = False
        for frame in container.decode(stream):
            if frame is not None:
                first_frame_found = True
                break

        if not first_frame_found:
            raise MediaProbeError(f"Video stream contains no decodable frames: {target}")

        return VideoMetadata(
            media_type="video/mp4" if target.suffix.lower() == ".mp4" else f"video/{target.suffix.lstrip('.')}",
            width=width,
            height=height,
            duration_ns=duration_ns,
            frame_rate_num=fps_num,
            frame_rate_den=fps_den,
            time_base_num=tb_num,
            time_base_den=tb_den,
        )
    finally:
        container.close()


def full_decode_audit(path: str | Path, max_frames: int | None = None) -> dict[str, Any]:
    """Perform a full frame-by-frame decode pass checking PTS continuity and integrity."""
    target = Path(path).resolve()
    container = None
    try:
        container = av.open(str(target))
        video_streams = container.streams.video
        if not video_streams:
            raise MediaProbeError("No video stream found for decode audit.")

        stream = video_streams[0]
        decoded_frames = 0
        missing_pts_count = 0
        last_pts: int | None = None
        discontinuities = 0

        for frame in container.decode(stream):
            decoded_frames += 1
            if frame.pts is None:
                missing_pts_count += 1
            else:
                if last_pts is not None and frame.pts <= last_pts:
                    discontinuities += 1
                last_pts = frame.pts

            if max_frames is not None and decoded_frames >= max_frames:
                break

        return {
            "path": str(target),
            "decoded_frames": decoded_frames,
            "missing_pts_count": missing_pts_count,
            "pts_discontinuities": discontinuities,
            "is_corrupt": False,
        }
    except Exception as exc:  # noqa: BLE001 - decoder may raise arbitrary library errors on corruption
        return {
            "path": str(target),
            "error": str(exc),
            "is_corrupt": True,
        }
    finally:
        if container is not None:
            container.close()
