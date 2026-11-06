#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration tests for the complete SLT Bilingual Core pipeline.
Tests both the modular core engine and the desktop adapter stack end-to-end.
"""
import pytest
import numpy as np
import time
from slt.recognition import extract_features, SLTClassifier
from slt.interaction import SLTInteractionEngine, InteractionState
from slt.language import BilingualTranslator
from slt_desktop.hand_landmarker import HandObservation
from slt_desktop.recognition_adapter import build_recognition_backend
from slt_desktop.translation_adapter import TranslationAdapter
from slt_desktop.subtitles import create_srt_content


def test_full_pipeline_flow():
    """Verify core recognition -> interaction -> language translation pipeline."""
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


def test_desktop_adapter_end_to_end_flow():
    """Verify desktop adapter chain: HandObservation -> Backend -> Translator -> Subtitles."""
    backend = build_recognition_backend()
    translator = TranslationAdapter()

    assert backend.ready is True
    assert translator.ready is True

    # Simulate sequence of observations
    points = np.zeros((21, 3), dtype=np.float32)
    obs = HandObservation(
        landmarks=points,
        world_landmarks=None,
        handedness="Right",
        detection_score=0.95
    )

    all_confirmed = []
    # Run multiple frames to test stability
    for ts_ms in range(0, 500, 40):
        evs = backend.process([obs], timestamp_ms=ts_ms)
        if evs:
            all_confirmed.extend(evs)

    # Directly verify translation of recognized glosses
    trans = translator.translate_glosses(["HOLA", "AGUA"])
    assert "agua" in trans["es"].lower()
    assert "water" in trans["en"].lower()

    # Generate subtitles from events
    mock_events = [
        {"label": "HOLA", "start_ms": 1000, "end_ms": 1800, "es": "¡Hola!", "en": "Hello!"},
        {"label": "AGUA", "start_ms": 2000, "end_ms": 3200, "es": "Agua, por favor.", "en": "Water, please."}
    ]
    srt = create_srt_content(mock_events)
    assert "1" in srt
    assert "HOLA" in srt
    assert "AGUA" in srt
    assert "00:00:01,000 --> 00:00:01,800" in srt
