"""Unit tests for SLT HandTracker."""
import pytest

from slt_core.domain import Handedness, HandObservation, Landmark
from slt_core.perception.errors import TrackingError
from slt_core.perception.tracking import HandTracker


def make_hand(
    x: float,
    side: Handedness,
    tracking_id: int | None = None,
) -> HandObservation:
    landmarks = tuple(
        Landmark(
            x=x + ((i % 3) - 1) * 0.001,
            y=0.4 + ((i % 4) - 1.5) * 0.001,
            z=0.0,
        )
        for i in range(21)
    )
    world = tuple(
        Landmark(x=float(i) * 0.001, y=float(i) * 0.002, z=float(i) * 0.003)
        for i in range(21)
    )
    return HandObservation(
        tracking_id=tracking_id,
        handedness=side,
        landmarks=landmarks,
        world_landmarks=world,
        handedness_score=0.98,
    )


def test_initial_id_assignment():
    tracker = HandTracker()
    hand_left = make_hand(x=0.3, side=Handedness.LEFT)
    hand_right = make_hand(x=0.7, side=Handedness.RIGHT)

    tracked = tracker.update(frame_index=0, observations=[hand_left, hand_right])
    assert len(tracked) == 2
    ids = {h.tracking_id for h in tracked}
    assert None not in ids
    assert len(ids) == 2


def test_persistent_tracking_across_frames():
    tracker = HandTracker(max_distance=0.20)
    h0 = make_hand(x=0.5, side=Handedness.RIGHT)

    tracked_f0 = tracker.update(frame_index=0, observations=[h0])
    orig_id = tracked_f0[0].tracking_id
    assert orig_id is not None

    # Frame 1: Hand moves slightly to x=0.52
    h1 = make_hand(x=0.52, side=Handedness.RIGHT)
    tracked_f1 = tracker.update(frame_index=1, observations=[h1])
    assert tracked_f1[0].tracking_id == orig_id

    # Frame 2: Hand moves to x=0.54
    h2 = make_hand(x=0.54, side=Handedness.RIGHT)
    tracked_f2 = tracker.update(frame_index=2, observations=[h2])
    assert tracked_f2[0].tracking_id == orig_id


def test_reordered_observations_preserve_id():
    tracker = HandTracker()
    left_f0 = make_hand(x=0.2, side=Handedness.LEFT)
    right_f0 = make_hand(x=0.8, side=Handedness.RIGHT)

    t0 = tracker.update(frame_index=0, observations=[left_f0, right_f0])
    left_id = t0[0].tracking_id
    right_id = t0[1].tracking_id

    # Frame 1: MediaPipe emits [Right, Left] (reversed order)
    right_f1 = make_hand(x=0.81, side=Handedness.RIGHT)
    left_f1 = make_hand(x=0.21, side=Handedness.LEFT)

    t1 = tracker.update(frame_index=1, observations=[right_f1, left_f1])
    # The first result in t1 is Right -> should match right_id
    assert t1[0].tracking_id == right_id
    # The second result in t1 is Left -> should match left_id
    assert t1[1].tracking_id == left_id


def test_temporary_occlusion_retains_id():
    tracker = HandTracker(max_missed_frames=5)
    h0 = make_hand(x=0.5, side=Handedness.RIGHT)
    t0 = tracker.update(frame_index=0, observations=[h0])
    orig_id = t0[0].tracking_id
    assert orig_id is not None

    # Temporary occlusion / disappearance for 3 frames (< 5 max_missed_frames)
    _ = tracker.update(frame_index=1, observations=[])
    _ = tracker.update(frame_index=2, observations=[])
    _ = tracker.update(frame_index=3, observations=[])

    # Hand reappears at frame 4 at proximate location (x=0.51) -> retains orig_id
    h4 = make_hand(x=0.51, side=Handedness.RIGHT)
    t4 = tracker.update(frame_index=4, observations=[h4])
    assert len(t4) == 1
    assert t4[0].tracking_id == orig_id


def test_track_expiration_after_max_missed_frames():
    tracker = HandTracker(max_missed_frames=5)
    h = make_hand(x=0.5, side=Handedness.RIGHT)
    t0 = tracker.update(frame_index=0, observations=[h])
    id_0 = t0[0].tracking_id

    # Miss 6 frames (frame 1 to 6)
    _ = tracker.update(frame_index=6, observations=[])

    # Hand reappears at frame 7 at the same location -> should get a NEW id because track expired
    h_new = make_hand(x=0.5, side=Handedness.RIGHT)
    t7 = tracker.update(frame_index=7, observations=[h_new])
    assert t7[0].tracking_id != id_0


def test_regressive_frame_index_raises():
    tracker = HandTracker()
    h = make_hand(x=0.5, side=Handedness.RIGHT)
    tracker.update(frame_index=5, observations=[h])

    with pytest.raises(TrackingError, match="must increase"):
        tracker.update(frame_index=4, observations=[h])

    with pytest.raises(TrackingError, match="must increase"):
        tracker.update(frame_index=5, observations=[h])


def test_reset_clears_tracks():
    tracker = HandTracker()
    h = make_hand(x=0.5, side=Handedness.RIGHT)
    tracker.update(frame_index=1, observations=[h])
    tracker.reset()

    # After reset, can accept frame_index=0 again and restarts ID numbering at 1
    t0 = tracker.update(frame_index=0, observations=[h])
    assert t0[0].tracking_id == 1


def test_tracking_aspect_ratio_weighting():
    # In 16:9, dx=0.2 is scaled by 16/9 (~1.778) -> ~0.3556, which exceeds max_distance=0.30
    widescreen_tracker = HandTracker(max_distance=0.30, aspect_ratio=16.0 / 9.0)
    h0 = make_hand(x=0.4, side=Handedness.RIGHT)
    t0 = widescreen_tracker.update(frame_index=0, observations=[h0])
    orig_id = t0[0].tracking_id

    # Hand moves dx=0.2 in x, dy=0. In 1:1, distance=0.20 <= 0.30.
    # In 16:9, distance = 0.2 * 1.778 = 0.3556 > 0.30 -> gets NEW ID due to aspect ratio penalty
    h1 = make_hand(x=0.6, side=Handedness.RIGHT)
    t1 = widescreen_tracker.update(frame_index=1, observations=[h1])
    assert t1[0].tracking_id != orig_id
