"""End-to-end integration test of the complete SLT pipeline."""
import numpy as np
import pytest

from slt.vision.landmark_extractor import extract_features
from slt.recognition.classifier import SLTClassifier
from slt.recognition.prediction_filter import PredictionFilter, FilterEvent
from slt.language.translator import BilingualTranslator
from slt.audio.speech_engine import SpeechEngine
from slt.utils.paths import SLT_MODEL_PATH, LEXICON_PATH

def test_full_pipeline_flow():
    if not SLT_MODEL_PATH.is_file():
        pytest.skip("slt_model.npz not generated")

    classifier = SLTClassifier(SLT_MODEL_PATH, k=5)
    pred_filter = PredictionFilter(window_size=6, minimum_votes=4, min_hold_frames=3, cooldown_sec=0.2)
    translator = BilingualTranslator(LEXICON_PATH)
    speech = SpeechEngine(rate=3)

    try:
        # Use a training sample vector from HOLA
        hola_idx = classifier.classes.index("HOLA")
        hola_mask = (classifier.y_train == hola_idx)
        hola_feat = classifier.X_train[hola_mask][0]

        # Simulate 4 consecutive frames of holding HOLA
        confirmed_sign = None
        for _ in range(4):
            label, conf, is_conf = classifier.predict(hola_feat)
            ev, s_label, _ = pred_filter.update(label, is_conf)
            if ev == FilterEvent.SIGN_CONFIRMED:
                confirmed_sign = s_label

        assert confirmed_sign == "HOLA"

        # Pass to translator
        trans = translator.add_gloss(confirmed_sign)
        assert "¡Hola!" in trans["es"]
        assert "Hello!" in trans["en"]

        # Enqueue speech without blocking
        speech.speak_bilingual(trans["es"], trans["en"], mode="both")
        speech.wait_until_done()

    finally:
        speech.stop()
