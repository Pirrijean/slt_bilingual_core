"""Unit tests for Video Presentation Timestamps and Fractions."""
from fractions import Fraction
from types import SimpleNamespace

import pytest

from slt_core.perception.errors import InvalidVideoTimestampError
from slt_core.sources.video import (
    _to_fraction,
    presentation_timestamp_ns,
)


def test_timestamp_with_fractional_time_base():
    timestamp = presentation_timestamp_ns(pts=1, time_base=Fraction(1, 30))
    # 1 * (1/30) * 1e9 = 33333333.33 -> integer 33_333_333 ns
    assert timestamp == 33_333_333


def test_variable_presentation_intervals():
    tb = Fraction(1, 30)
    t0 = presentation_timestamp_ns(pts=0, time_base=tb)
    t1 = presentation_timestamp_ns(pts=1, time_base=tb)
    t3 = presentation_timestamp_ns(pts=3, time_base=tb)

    assert t0 == 0
    assert t1 == 33_333_333
    assert t3 == 100_000_000
    # Difference between frame 1 and 3 (2 frames apart) is 2 * 33_333_333 = 66_666_667
    assert (t3 - t1) == pytest.approx(66_666_667, abs=1)


def test_to_fraction_conversion():
    # Native Fraction
    assert _to_fraction(Fraction(1, 25)) == Fraction(1, 25)

    # Object with numerator and denominator (e.g. PyAV time_base)
    pyav_mock = SimpleNamespace(numerator=1, denominator=90000)
    assert _to_fraction(pyav_mock) == Fraction(1, 90000)

    # Invalid denominator <= 0
    bad_obj = SimpleNamespace(numerator=1, denominator=0)
    with pytest.raises(InvalidVideoTimestampError, match="Denominator"):
        _to_fraction(bad_obj)

    # Completely invalid object
    with pytest.raises(InvalidVideoTimestampError, match="Cannot convert"):
        _to_fraction("not a fraction")


def test_missing_or_negative_pts_raises():
    tb = Fraction(1, 30)
    with pytest.raises(InvalidVideoTimestampError, match="lacks PTS"):
        presentation_timestamp_ns(pts=None, time_base=tb)

    with pytest.raises(InvalidVideoTimestampError, match="Negative"):
        presentation_timestamp_ns(pts=-5, time_base=tb)


def test_invalid_time_base_raises():
    # Denominator <= 0
    with pytest.raises(InvalidVideoTimestampError, match="strictly positive"):
        presentation_timestamp_ns(pts=1, time_base=SimpleNamespace(numerator=1, denominator=0))
