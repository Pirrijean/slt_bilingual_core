"""Unit tests for Phase 2.5 temporal and timestamp contracts."""
from __future__ import annotations

import pytest

from slt_core.errors import ValidationError
from slt_core.temporal.timestamps import (
    SourceTimestamp,
    TimestampKind,
    TimestampResolutionError,
)


def test_source_timestamp_valid_monotonic():
    ts = SourceTimestamp(
        kind=TimestampKind.MONOTONIC,
        timestamp_ns=1_000_000_000,
    )
    assert ts.kind == TimestampKind.MONOTONIC
    assert ts.timestamp_ns == 1_000_000_000
    assert ts.pts is None


def test_source_timestamp_valid_presentation():
    ts = SourceTimestamp(
        kind=TimestampKind.PRESENTATION,
        timestamp_ns=2_000_000_000,
        pts=60,
        time_base_num=1,
        time_base_den=30,
    )
    assert ts.kind == TimestampKind.PRESENTATION
    assert ts.pts == 60
    assert ts.time_base_num == 1
    assert ts.time_base_den == 30


def test_source_timestamp_negative_raises():
    with pytest.raises(ValidationError, match="cannot be negative"):
        SourceTimestamp(
            kind=TimestampKind.MONOTONIC,
            timestamp_ns=-1,
        )


def test_source_timestamp_mismatched_time_base_raises():
    with pytest.raises(ValidationError, match="both be set or null"):
        SourceTimestamp(
            kind=TimestampKind.PRESENTATION,
            timestamp_ns=1000,
            pts=1,
            time_base_num=1,
            time_base_den=None,
        )


def test_source_timestamp_invalid_time_base_values_raises():
    with pytest.raises(ValidationError, match="strictly positive"):
        SourceTimestamp(
            kind=TimestampKind.PRESENTATION,
            timestamp_ns=1000,
            pts=1,
            time_base_num=0,
            time_base_den=30,
        )


def test_timestamp_resolution_error():
    err = TimestampResolutionError("Collision in millisecond conversion.")
    assert isinstance(err, ValueError)
