"""Unit tests for SLT MotionAnalyzer."""
import pytest

from slt_core.domain import (
    Handedness,
    HandObservation,
    Landmark,
    PerceptionFrame,
)
from slt_core.perception.errors import MotionError
from slt_core.perception.motion import MotionAnalyzer


def make_hand(x: float, track_id: int = 1) -> HandObservation:
    landmarks = tuple(Landmark(x=x, y=0.5, z=0.0) for _ in range(21))
    return HandObservation(
        tracking_id=track_id,
        handedness=Handedness.RIGHT,
        landmarks=landmarks,
        world_landmarks=landmarks,
        handedness_score=0.98,
    )


def make_frame(
    timestamp_ns: int,
    x: float,
    track_id: int = 1,
    source_id: str = "test",
) -> PerceptionFrame:
    return PerceptionFrame(
        source_id=source_id,
        frame_index=0,
        timestamp_ns=timestamp_ns,
        hands=(make_hand(x=x, track_id=track_id),),
    )


def test_motion_first_frame_has_no_motion():
    analyzer = MotionAnalyzer()
    f0 = make_frame(timestamp_ns=1_000_000_000, x=0.2)
    motions = analyzer.update(f0)
    assert motions == ()


def test_motion_second_frame_velocity_and_speed():
    analyzer = MotionAnalyzer()
    # Frame 0 at t=1.0s, x=0.2
    analyzer.update(make_frame(timestamp_ns=1_000_000_000, x=0.2))

    # Frame 1 at t=1.1s (dt=0.1s), x=0.3 (dx=0.1) -> vx = 1.0, vy = 0.0, speed = 1.0
    f1 = make_frame(timestamp_ns=1_100_000_000, x=0.3)
    motions = analyzer.update(f1)
    assert len(motions) == 1
    m = motions[0]
    assert m.tracking_id == 1
    assert m.delta_time_seconds == pytest.approx(0.1)
    assert m.velocity_x == pytest.approx(1.0)
    assert m.velocity_y == pytest.approx(0.0)
    assert m.speed == pytest.approx(1.0)


def test_motion_gap_exceeds_max_delta():
    analyzer = MotionAnalyzer(max_delta_time_seconds=0.5)
    analyzer.update(make_frame(timestamp_ns=1_000_000_000, x=0.2))

    # Next frame arrives 1.0 second later (> 0.5s)
    f_late = make_frame(timestamp_ns=2_000_000_000, x=0.4)
    motions = analyzer.update(f_late)
    # Motion should be suppressed due to large gap
    assert motions == ()


def test_motion_single_source_binding():
    analyzer = MotionAnalyzer()
    analyzer.update(make_frame(timestamp_ns=1_000_000_000, x=0.2, source_id="cam_A"))

    with pytest.raises(MotionError, match="must be bound to one source"):
        analyzer.update(make_frame(timestamp_ns=1_100_000_000, x=0.3, source_id="cam_B"))


def test_motion_regressive_timestamp_raises():
    analyzer = MotionAnalyzer()
    analyzer.update(make_frame(timestamp_ns=2_000_000_000, x=0.2))

    with pytest.raises(MotionError, match="must increase"):
        analyzer.update(make_frame(timestamp_ns=1_500_000_000, x=0.3))


def test_motion_reset():
    analyzer = MotionAnalyzer()
    analyzer.update(make_frame(timestamp_ns=1_000_000_000, x=0.2, source_id="cam_A"))
    analyzer.reset()

    # After reset, can accept new source without error
    analyzer.update(make_frame(timestamp_ns=1_000_000_000, x=0.2, source_id="cam_B"))
