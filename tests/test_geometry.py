"""Unit tests for SLT Hand Geometry Engine."""
from math import isfinite

import pytest

from slt_core.domain import Handedness, HandObservation, Landmark
from slt_core.perception.errors import GeometryError
from slt_core.perception.geometry import (
    angle_degrees,
    compute_hand_geometry,
    euclidean_distance,
)


def make_hand(wrist_x: float = 0.5, wrist_y: float = 0.7) -> HandObservation:
    # Build 21 landmarks representing a standard hand configuration
    landmarks = []
    for i in range(21):
        landmarks.append(
            Landmark(
                x=wrist_x + float(i % 5) * 0.03,
                y=wrist_y - float(i // 4) * 0.04,
                z=0.0,
            )
        )
    world = tuple(
        Landmark(x=float(i) * 0.001, y=float(i) * 0.002, z=0.0)
        for i in range(21)
    )
    return HandObservation(
        tracking_id=1,
        handedness=Handedness.RIGHT,
        landmarks=tuple(landmarks),
        world_landmarks=world,
        handedness_score=0.98,
    )


def test_euclidean_distance():
    p1 = Landmark(0.0, 0.0, 0.0)
    p2 = Landmark(3.0, 4.0, 0.0)
    assert euclidean_distance(p1, p2) == pytest.approx(5.0)


def test_angle_degrees():
    # 90 degree angle
    p1 = Landmark(1.0, 0.0, 0.0)
    vertex = Landmark(0.0, 0.0, 0.0)
    p2 = Landmark(0.0, 1.0, 0.0)
    assert angle_degrees(p1, vertex, p2) == pytest.approx(90.0)

    # 180 degree collinear
    p3 = Landmark(-1.0, 0.0, 0.0)
    assert angle_degrees(p1, vertex, p3) == pytest.approx(180.0)

    # Coincident raises GeometryError
    with pytest.raises(GeometryError, match="coincident"):
        angle_degrees(p1, p1, p2)


def test_compute_hand_geometry_features():
    hand = make_hand()
    geom = compute_hand_geometry(hand)

    assert geom.tracking_id == 1
    assert geom.bounding_box.x_min < geom.bounding_box.x_max
    assert geom.bounding_box.y_min < geom.bounding_box.y_max
    assert geom.palm_width > 0.0
    assert geom.wrist_to_middle_mcp > 0.0

    assert isfinite(geom.palm_center.x)
    assert isfinite(geom.palm_center.y)

    assert len(geom.relative_landmarks) == 21
    # The relative wrist (landmark 0) must be (0, 0, 0)
    rel_wrist = geom.relative_landmarks[0]
    assert rel_wrist.x == pytest.approx(0.0, abs=1e-6)
    assert rel_wrist.y == pytest.approx(0.0, abs=1e-6)
    assert rel_wrist.z == pytest.approx(0.0, abs=1e-6)


def test_compute_hand_geometry_degenerate_raises():
    # Degenerate hand where all landmarks are identical (palm width = 0)
    same_lm = Landmark(0.5, 0.5, 0.0)
    hand_collapsed = HandObservation(
        tracking_id=1,
        handedness=Handedness.RIGHT,
        landmarks=tuple(same_lm for _ in range(21)),
        world_landmarks=tuple(same_lm for _ in range(21)),
    )
    with pytest.raises(GeometryError, match="Palm width is zero"):
        compute_hand_geometry(hand_collapsed)
