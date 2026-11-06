"""Unit tests for the SLT classifier and temporal prediction filter."""
import numpy as np
import pytest
from slt.recognition.classifier import SLTClassifier
from slt.recognition.prediction_filter import PredictionFilter, FilterEvent
from slt.utils.paths import SLT_MODEL_PATH

def test_classifier_prediction():
    if not SLT_MODEL_PATH.is_file():
        pytest.skip("slt_model.npz not generated yet")

    classifier = SLTClassifier(SLT_MODEL_PATH, k=5)
    assert len(classifier.classes) == 19

    # Test with training sample
    sample_feat = classifier.X_train[0]
    pred_label, conf, is_conf = classifier.predict(sample_feat)

    assert pred_label in classifier.classes
    assert 0.0 <= conf <= 1.0

def test_classifier_unknown_rejection():
    if not SLT_MODEL_PATH.is_file():
        pytest.skip("slt_model.npz not generated yet")

    classifier = SLTClassifier(SLT_MODEL_PATH, k=5, distance_threshold=2.5)
    # Synthetic aberrant feature vector far outside anatomical distribution
    garbage_feat = np.full((106,), 999.0, dtype=np.float32)
    pred_label, conf, is_conf = classifier.predict(garbage_feat)

    # Must reject unknown/aberrant vectors
    assert not is_conf
    assert pred_label == "_NADA_"

def test_prediction_filter_streak_and_debounce():
    pfilter = PredictionFilter(window_size=6, minimum_votes=4, min_hold_frames=3, cooldown_sec=0.2)

    # 1. First 2 frames: not enough streak
    ev1, l1, _ = pfilter.update("HOLA", is_confident=True)
    assert ev1 == FilterEvent.NONE

    ev2, l2, _ = pfilter.update("HOLA", is_confident=True)
    assert ev2 == FilterEvent.NONE

    # 3. Third frame: confirms HOLA!
    ev3, l3, _ = pfilter.update("HOLA", is_confident=True)
    assert ev3 == FilterEvent.SIGN_CONFIRMED
    assert l3 == "HOLA"

    # 4. Fourth frame: immediately holding HOLA should not repeat confirmation!
    ev4, l4, _ = pfilter.update("HOLA", is_confident=True)
    assert ev4 == FilterEvent.NONE

    # 5. Hand release back to _NADA_
    for _ in range(5):
        ev, _, _ = pfilter.update("_NADA_", is_confident=True)
    assert pfilter.released
