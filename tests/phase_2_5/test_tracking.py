"""Unit tests for Phase 2.5 tracking association and aspect ratio scaling."""
from __future__ import annotations

from slt_core.domain import Handedness, HandObservation, Landmark
from slt_core.perception.tracking import HandTracker


def make_obs(x: float, y: float, handedness: Handedness) -> HandObservation:
    lms = tuple(Landmark(x=x, y=y, z=0.0) for _ in range(21))
    return HandObservation(
        tracking_id=None,
        handedness=handedness,
        landmarks=lms,
        world_landmarks=lms,
        handedness_score=0.95,
    )


def test_tracking_aspect_ratio_consistency():
    tracker = HandTracker(max_distance=0.3, aspect_ratio=1920.0 / 1080.0)

    # Frame 0
    obs0 = (make_obs(0.5, 0.5, Handedness.RIGHT),)
    res0 = tracker.update(frame_index=0, observations=obs0)
    assert len(res0) == 1
    t0_id = res0[0].tracking_id
    assert t0_id is not None

    # Frame 1: slight vertical shift
    obs1 = (make_obs(0.5, 0.52, Handedness.RIGHT),)
    res1 = tracker.update(frame_index=1, observations=obs1)
    assert len(res1) == 1
    assert res1[0].tracking_id == t0_id


def test_tracking_two_hands_identity_preservation():
    tracker = HandTracker(max_distance=0.3)

    # Initial frame with two hands (left and right)
    obs0 = (
        make_obs(0.3, 0.5, Handedness.LEFT),
        make_obs(0.7, 0.5, Handedness.RIGHT),
    )
    res0 = tracker.update(frame_index=0, observations=obs0)
    assert len(res0) == 2
    id_left = res0[0].tracking_id
    id_right = res0[1].tracking_id
    assert id_left != id_right

    # Reordered input on frame 1
    obs1 = (
        make_obs(0.71, 0.5, Handedness.RIGHT),
        make_obs(0.31, 0.5, Handedness.LEFT),
    )
    res1 = tracker.update(frame_index=1, observations=obs1)
    assigned_ids = {r.handedness: r.tracking_id for r in res1}
    assert assigned_ids[Handedness.LEFT] == id_left
    assert assigned_ids[Handedness.RIGHT] == id_right
