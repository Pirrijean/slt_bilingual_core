"""Unit tests for Phase 2.5 21-joint motion kinematics."""
from __future__ import annotations

import pytest

from slt_core.domain import Handedness, HandObservation, Landmark
from slt_core.perception.errors import MotionError
from slt_core.perception.motion import MotionAnalyzer


def make_hand(offset_x: float, tracking_id: int = 1) -> HandObservation:
    lms = tuple(Landmark(x=offset_x + i * 0.01, y=0.5, z=0.0) for i in range(21))
    return HandObservation(
        tracking_id=tracking_id,
        handedness=Handedness.RIGHT,
        landmarks=lms,
        world_landmarks=lms,
        handedness_score=0.99,
    )


def test_motion_21_joints_calculation():
    analyzer = MotionAnalyzer(max_delta_time_seconds=0.5)

    # Initial frame
    m0 = analyzer.update(
        target_or_source="cam_1",
        timestamp_ns=1_000_000_000,
        hands=(make_hand(offset_x=0.2),),
        image_width=1920,
        image_height=1080,
    )
    assert m0 == ()

    # Frame 1 after dt = 0.1s, dx = 0.05
    m1 = analyzer.update(
        target_or_source="cam_1",
        timestamp_ns=1_100_000_000,
        hands=(make_hand(offset_x=0.25),),
        image_width=1920,
        image_height=1080,
    )
    assert len(m1) == 1
    motion = m1[0]
    assert motion.tracking_id == 1
    assert motion.delta_time_seconds == pytest.approx(0.1)
    assert len(motion.joints) == 21
    assert motion.wrist.velocity_x > 0
    assert motion.wrist.speed > 0


def test_motion_single_source_enforcement():
    analyzer = MotionAnalyzer()
    analyzer.update(
        target_or_source="source_A",
        timestamp_ns=1_000_000_000,
        hands=(make_hand(offset_x=0.2),),
        image_width=1920,
        image_height=1080,
    )

    with pytest.raises(MotionError, match="must be bound to one source"):
        analyzer.update(
            target_or_source="source_B",
            timestamp_ns=1_100_000_000,
            hands=(make_hand(offset_x=0.22),),
            image_width=1920,
            image_height=1080,
        )
