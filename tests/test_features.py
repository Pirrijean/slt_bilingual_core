"""Unit tests for the 106-D landmark feature extractor."""
import numpy as np
import pytest
from slt.vision.landmark_extractor import (
    extract_features, normalize_landmarks, joint_angle
)

def test_joint_angle_collinear():
    a = np.array([0.0, 0.0, 0.0])
    b = np.array([0.0, 1.0, 0.0])
    c = np.array([0.0, 2.0, 0.0])
    # Straight line: angle is pi (180 deg)
    assert np.isclose(joint_angle(a, b, c), np.pi, atol=1e-3)

def test_joint_angle_perpendicular():
    a = np.array([1.0, 0.0, 0.0])
    b = np.array([0.0, 0.0, 0.0])
    c = np.array([0.0, 1.0, 0.0])
    # Right angle: pi / 2
    assert np.isclose(joint_angle(a, b, c), np.pi / 2, atol=1e-3)

def test_feature_dimension_and_no_nan():
    rng = np.random.default_rng(123)
    points = rng.uniform(0.1, 0.9, size=(21, 3)).astype(np.float32)
    feats = extract_features(points, handedness="Right")

    assert feats.shape == (106,)
    assert np.all(np.isfinite(feats))
    assert not np.any(np.isnan(feats))

def test_translation_invariance():
    rng = np.random.default_rng(456)
    points = rng.uniform(0.1, 0.8, size=(21, 3)).astype(np.float32)
    shift = np.array([10.5, -3.2, 7.8], dtype=np.float32)

    f1 = extract_features(points, handedness="Right")
    f2 = extract_features(points + shift, handedness="Right")

    # Features must be identical regardless of global camera position
    assert np.allclose(f1, f2, atol=1e-4)

def test_scale_invariance():
    rng = np.random.default_rng(789)
    points = rng.uniform(0.1, 0.8, size=(21, 3)).astype(np.float32)

    f1 = extract_features(points, handedness="Right")
    f2 = extract_features(points * 2.5, handedness="Right")

    # Features must be invariant to hand distance / scaling
    assert np.allclose(f1, f2, atol=1e-4)
