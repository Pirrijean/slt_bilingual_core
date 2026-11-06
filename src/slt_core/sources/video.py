"""PyAV-based Video File FrameSource preserving presentation timestamps."""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Any

from slt_core.domain import FramePacket
from slt_core.perception.errors import (
    InvalidVideoTimestampError,
    VideoDecodeError,
    VideoOpenError,
)
from slt_core.perception.image import validate_bgr_frame


def _to_fraction(value: Any) -> Fraction:
    """Convert an arbitrary fraction-like object to Python fractions.Fraction."""
    try:
        numerator = int(value.numerator)
        denominator = int(value.denominator)
        if denominator <= 0:
            raise ValueError("Denominator must be strictly positive.")
        return Fraction(numerator, denominator)
    except Exception as exc:
        raise InvalidVideoTimestampError(f"Cannot convert time_base to Fraction: {exc}") from exc


def presentation_timestamp_ns(pts: int | None, time_base: Fraction) -> int:
    """
    Calculate normalized presentation timestamp in nanoseconds from PTS and time_base.
    Formula: t_ns = (pts * time_base.num * 1_000_000_000) // time_base.den
    """
    if pts is None:
        raise InvalidVideoTimestampError("Video frame lacks PTS presentation timestamp.")
    if time_base.denominator <= 0:
        raise InvalidVideoTimestampError("time_base denominator must be strictly positive.")

    val_ns = (pts * time_base.numerator * 1_000_000_000) // time_base.denominator
    if val_ns < 0:
        raise InvalidVideoTimestampError(f"Negative presentation timestamp: {val_ns} ns.")
    return val_ns


class VideoSource:
    """
    Decodes video files sequentially using PyAV, preserving exact
    presentation timestamps (PTS x time_base) for variable frame rate (VFR) fidelity.
    """

    def __init__(
        self,
        file_path: str | Path,
        source_id: str | None = None,
    ) -> None:
        self.file_path = Path(file_path).resolve()
        if not self.file_path.is_file():
            raise VideoOpenError(f"Video file not found: {self.file_path}")

        self._source_id = source_id or self.file_path.stem
        self._frame_index = 0
        self._last_timestamp_ns: int | None = None
        self._container: Any | None = None
        self._frame_iterator: Any | None = None
        self._time_base: Fraction = Fraction(1, 1000)
        self._is_open = False

        self._open()

    def _open(self) -> None:
        try:
            import av
            self._container = av.open(str(self.file_path))
            if not self._container.streams.video:
                raise VideoOpenError(f"No video streams found in file: {self.file_path}")
            video_stream = self._container.streams.video[0]
            self._time_base = _to_fraction(video_stream.time_base)
            self._frame_iterator = self._container.decode(video=0)
            self._is_open = True
        except Exception as exc:
            self.close()
            if isinstance(exc, VideoOpenError):
                raise
            raise VideoOpenError(f"Failed to open video container: {exc}") from exc

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def ready(self) -> bool:
        return self._is_open and self._container is not None

    def read(self) -> FramePacket | None:
        """
        Decode and return the next video FramePacket.
        Returns None at natural end-of-stream.
        Raises InvalidVideoTimestampError if timestamps are non-monotonic or missing.
        """
        if not self.ready or self._frame_iterator is None:
            return None

        try:
            frame = next(self._frame_iterator)
        except StopIteration:
            return None
        except Exception as exc:
            raise VideoDecodeError(f"Error decoding frame {self._frame_index}: {exc}") from exc

        # Resolve exact time_base and calculate presentation timestamp
        tb = _to_fraction(frame.time_base if frame.time_base is not None else self._time_base)
        timestamp_ns = presentation_timestamp_ns(frame.pts, tb)

        if self._last_timestamp_ns is not None and timestamp_ns <= self._last_timestamp_ns:
            raise InvalidVideoTimestampError(
                f"Non-monotonic presentation timestamp: previous {self._last_timestamp_ns} ns, "
                f"current {timestamp_ns} ns at frame {self._frame_index}."
            )
        self._last_timestamp_ns = timestamp_ns

        # Convert video frame to BGR24 numpy array
        bgr_image = frame.to_ndarray(format="bgr24")

        raw_packet = FramePacket(
            source_id=self._source_id,
            frame_index=self._frame_index,
            timestamp_ns=timestamp_ns,
            image=bgr_image,
            pixel_format="BGR24",
            timestamp_kind="presentation",
            presentation_pts=frame.pts,
            time_base_num=tb.numerator,
            time_base_den=tb.denominator,
        )
        validated_image = validate_bgr_frame(raw_packet)

        current_index = self._frame_index
        self._frame_index += 1

        return FramePacket(
            source_id=raw_packet.source_id,
            frame_index=current_index,
            timestamp_ns=raw_packet.timestamp_ns,
            image=validated_image,
            pixel_format=raw_packet.pixel_format,
            timestamp_kind=raw_packet.timestamp_kind,
            presentation_pts=raw_packet.presentation_pts,
            time_base_num=raw_packet.time_base_num,
            time_base_den=raw_packet.time_base_den,
        )

    def close(self) -> None:
        """Release video container resources idempotently."""
        if self._container is not None:
            try:
                self._container.close()
            except Exception:  # noqa: BLE001, S110
                pass
            self._container = None
        self._frame_iterator = None
        self._is_open = False
