"""Temporal and timestamp representation for SLT perception and video sources."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from slt_core.errors import ValidationError


class TimestampKind(StrEnum):
    """Source domain of the timestamp."""

    MONOTONIC = "monotonic"
    PRESENTATION = "presentation"


class TimestampResolutionError(ValueError):
    """Raised when timestamp conversion or millisecond mapping fails."""


@dataclass(frozen=True, slots=True)
class SourceTimestamp:
    """Immutable representation of original source timing."""

    kind: TimestampKind
    timestamp_ns: int
    pts: int | None = None
    time_base_num: int | None = None
    time_base_den: int | None = None

    def __post_init__(self) -> None:
        if self.timestamp_ns < 0:
            raise ValidationError("Timestamp cannot be negative.")
        if (self.time_base_num is None) != (self.time_base_den is None):
            raise ValidationError("time_base_num and time_base_den must both be set or null.")
        if (
            self.time_base_num is not None
            and self.time_base_den is not None
            and (self.time_base_num <= 0 or self.time_base_den <= 0)
        ):
            raise ValidationError("Time base components must be strictly positive.")
