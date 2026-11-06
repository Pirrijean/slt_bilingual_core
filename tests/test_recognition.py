import pytest
import numpy as np
from slt.recognition import extract_features, SLTClassifier

def test_joint_angle_calculation():
    # Perpendicular vectors should have angle pi/2 (approx 1.5708)
    from slt.recognition import compute_angle
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    angle = compute_angle(v1, v2)
    assert pytest.approx(angle, rel=1e-3) == np.pi / 2.0

def test_feature_dimension_and_no_nan():
    rng = np.random.RandomState(42)
    pts = rng.rand(21, 3).astype(np.float32)
    feats = extract_features(pts)
    assert feats.shape == (106,)
    assert not np.isnan(feats).any()
    assert not np.isinf(feats).any()

def test_translation_invariance():
    rng = np.random.RandomState(123)
    pts = rng.rand(21, 3).astype(np.float32)
    feats_orig = extract_features(pts)
    pts_shifted = pts + np.array([15.5, -20.2, 8.4], dtype=np.float32)
    feats_shifted = extract_features(pts_shifted)
    np.testing.assert_allclose(feats_orig, feats_shifted, atol=1e-4)

def test_scale_invariance():
    rng = np.random.RandomState(456)
    pts = rng.rand(21, 3).astype(np.float32)
    feats_orig = extract_features(pts)
    pts_scaled = pts * 3.5
    feats_scaled = extract_features(pts_scaled)
    np.testing.assert_allclose(feats_orig, feats_scaled, atol=1e-4)

def test_classifier_prediction_and_rejection():
    clf = SLTClassifier()
    if len(clf.classes) > 0:
        # Known centroid prediction
        dummy_feat = clf.feature_mean.copy()
        pred, conf, is_valid = clf.predict(dummy_feat)
        assert isinstance(pred, str)
        assert 0.0 <= conf <= 1.0

        # Outlier rejection with extreme values
        extreme_feat = np.ones(106, dtype=np.float32) * 999.0
        pred_out, conf_out, is_valid_out = clf.predict(extreme_feat)
        assert pred_out == "_NADA_" or not is_valid_out
