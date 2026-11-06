#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for slt_desktop.drawing module.
Verifies clean anatomical drawing overlays for Mode B.
"""
import numpy as np
from slt_desktop.drawing import draw_hand_landmarks, HAND_CONNECTIONS, FINGERTIP_INDICES
from slt_desktop.hand_landmarker import HandObservation


def test_draw_hand_landmarks_empty():
    """Verify drawing on empty observations returns unmodified frame."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    out = draw_hand_landmarks(frame, [])
    np.testing.assert_array_equal(frame, out)


def test_draw_hand_landmarks_renders_overlay():
    """Verify landmarks and connections render onto frame without modifying input in-place."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 21 landmarks centered in frame
    lms = np.full((21, 3), 0.5, dtype=np.float32)
    obs = HandObservation(
        landmarks_norm=lms,
        landmarks_world=None,
        handedness="Right",
        score=0.9
    )

    out = draw_hand_landmarks(frame, [obs])
    assert out.shape == frame.shape
    assert out.dtype == frame.dtype
    # The output should have non-zero pixels rendered
    assert np.count_nonzero(out) > 0
    # Original frame must remain black (no in-place corruption)
    assert np.count_nonzero(frame) == 0
