"""Unit tests for Phase 2.5 independent 2D and 3D geometry contracts."""
from __future__ import annotations

import pytest

from slt_core.domain import Handedness, HandObservation, Landmark
from slt_core.perception.errors import GeometryError
from slt_core.perception.geometry import (
    compute_hand_geometry_2d,
    compute_hand_geometry_3d,
)


def make_test_hand() -> HandObservation:
    lms = tuple(Landmark(x=i * 0.04, y=i * 0.03, z=i * 0.01) for i in range(21))
    return HandObservation(
        tracking_id=42,
        handedness=Handedness.RIGHT,
        landmarks=lms,
        world_landmarks=lms,
        handedness_score=0.95,
    )


def test_compute_hand_geometry_2d_pixels():
    hand = make_test_hand()
    geom_2d = compute_hand_geometry_2d(hand, width=1920, height=1080)

    assert geom_2d.tracking_id == 42
    assert geom_2d.palm_width_px > 0
    assert geom_2d.bounding_box.x_min_px >= 0
    assert geom_2d.bounding_box.x_max_px <= 1920
    assert geom_2d.bounding_box.y_max_px <= 1080
    assert len(geom_2d.relative_landmarks) == 21
    assert len(geom_2d.finger_angles_deg) == 5


def test_compute_hand_geometry_2d_invalid_dims_raises():
    hand = make_test_hand()
    with pytest.raises(GeometryError, match="positive integers"):
        compute_hand_geometry_2d(hand, width=0, height=1080)


def test_compute_hand_geometry_3d_world():
    hand = make_test_hand()
    geom_3d = compute_hand_geometry_3d(hand)

    assert geom_3d.tracking_id == 42
    assert len(geom_3d.world_landmarks) == 21
    assert len(geom_3d.joint_angles_deg) == 10
    assert geom_3d.world_landmarks[0].x_m == 0.0
