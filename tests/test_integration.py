import pytest
import numpy as np
import time
from slt.recognition import extract_features, SLTClassifier
from slt.interaction import SLTInteractionEngine, InteractionState
from slt.language import BilingualTranslator

def test_full_pipeline_flow():
    # 1. Feature extractor with random landmarks
    rng = np.random.RandomState(42)
    fake_landmarks = rng.rand(21, 3).astype(np.float32)
    features = extract_features(fake_landmarks)
    assert features.shape == (106,)

    # 2. Classifier
    clf = SLTClassifier()
    pred, conf, is_valid = clf.predict(features)
    assert isinstance(pred, str)
    assert isinstance(conf, float)

    # 3. Interaction Engine
    interaction = SLTInteractionEngine(window_size=5, quorum_count=3, min_hold_seconds=0.01)
    confirmed_events = []
    interaction.sign_confirmed.connect(lambda ev: confirmed_events.append(ev))

    # Feed frames to trigger confirmation of 'HOLA'
    interaction.process_frame(has_hands=True, raw_prediction="HOLA", confidence=0.9, is_valid=True)
    interaction.process_frame(has_hands=True, raw_prediction="HOLA", confidence=0.9, is_valid=True)
    time.sleep(0.02)
    state = interaction.process_frame(has_hands=True, raw_prediction="HOLA", confidence=0.9, is_valid=True)

    assert len(confirmed_events) == 1
    assert confirmed_events[0].label == "HOLA"

    # 4. Bilingual Language Engine
    translator = BilingualTranslator()
    es, en = translator.add_gloss(confirmed_events[0].label)
    assert len(es) > 0
    assert len(en) > 0
    assert "¡Hola!" in es
    assert "Hello!" in en
