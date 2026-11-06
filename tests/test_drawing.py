#!/usr/bin/env python3
"""
Tests for slt_desktop.drawing module.
Verifies clean anatomical drawing overlays for Mode B.
"""
import numpy as np

from slt_desktop.drawing import draw_hand_landmarks
from slt_desktop.hand_landmarker import HandObservation


def test_drawing_preserves_frame_dimensions():
    """Verify test from section 7.2 preserving frame shape with synthetic landmarks."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    points = np.zeros((21, 3), dtype=np.float32)
    points[:, 0] = np.linspace(0.2, 0.8, 21)
    points[:, 1] = np.linspace(0.2, 0.8, 21)

    observation = HandObservation(
        landmarks=points,
        world_landmarks=points,
        handedness="Right",
        detection_score=0.95
    )

    result = draw_hand_landmarks(frame.copy(), [observation])
    assert result.shape == frame.shape


def test_draw_hand_landmarks_empty():
    """Verify drawing on empty observations returns unmodified frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_hand_landmarks(frame, [])
    np.testing.assert_array_equal(frame, out)


def test_draw_hand_landmarks_renders_overlay():
    """Verify landmarks render onto frame without modifying input in-place."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    lms = np.full((21, 3), 0.5, dtype=np.float32)
    obs = HandObservation(
        landmarks=lms,
        world_landmarks=None,
        handedness="Right",
        detection_score=0.9
    )

    out = draw_hand_landmarks(frame, [obs])
    assert out.shape == frame.shape
    assert out.dtype == frame.dtype
    assert np.count_nonzero(out) > 0
    assert np.count_nonzero(frame) == 0
