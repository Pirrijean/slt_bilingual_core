#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for slt_desktop.hand_landmarker module.
Verifies HandObservation dataclass and SLTHandLandmarker lifecycle.
"""
import pytest
import numpy as np
from pathlib import Path
from slt_desktop.hand_landmarker import HandObservation, SLTHandLandmarker
from slt.utils.paths import HAND_LANDMARKER_MODEL


def test_hand_observation_dataclass():
    """Verify HandObservation instantiation and attributes."""
    dummy_norm = np.zeros((21, 3), dtype=np.float32)
    dummy_world = np.zeros((21, 3), dtype=np.float32)
    obs = HandObservation(
        landmarks_norm=dummy_norm,
        landmarks_world=dummy_world,
        handedness="Right",
        score=0.95
    )
    assert obs.landmarks_norm.shape == (21, 3)
    assert obs.handedness == "Right"
    assert obs.score == 0.95


def test_slt_hand_landmarker_lifecycle_and_monotonicity():
    """Verify SLTHandLandmarker initialization, inference and monotonically increasing timestamps."""
    if not Path(HAND_LANDMARKER_MODEL).is_file():
        pytest.skip("hand_landmarker.task model not present.")

    detector = SLTHandLandmarker(model_path=HAND_LANDMARKER_MODEL, num_hands=2)
    assert detector._landmarker is not None

    # Black frame test (no hands)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    res1 = detector.detect(dummy_frame, timestamp_ms=100)
    assert isinstance(res1, list)
    assert len(res1) == 0

    # Test monotonic timestamp enforcement when passing same timestamp
    res2 = detector.detect(dummy_frame, timestamp_ms=100)
    assert detector._last_timestamp_ms == 101  # Enforced +1 ms

    # Clean close
    detector.close()
    assert detector._landmarker is None
