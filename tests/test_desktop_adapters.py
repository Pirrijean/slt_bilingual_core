#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for slt_desktop.recognition_adapter and slt_desktop.translation_adapter.
Verifies contract compliance, FSM integration, and bilingual translation.
"""
import pytest
import numpy as np
from slt_desktop.hand_landmarker import HandObservation
from slt_desktop.recognition_adapter import build_recognition_backend, SLTRecognitionBackend
from slt_desktop.translation_adapter import TranslationAdapter


def test_translation_adapter():
    """Verify TranslationAdapter produces simultaneous Spanish and English sentences."""
    adapter = TranslationAdapter()

    # Empty test
    empty = adapter.translate_glosses([])
    assert empty == {"es": "", "en": ""}

    # Greetings
    greet = adapter.translate_glosses(["HOLA"])
    assert "Hola" in greet["es"]
    assert "Hello" in greet["en"]

    # Needs / Water
    water = adapter.translate_glosses(["YO", "QUERER", "AGUA"])
    assert "agua" in water["es"].lower()
    assert "water" in water["en"].lower()


def test_recognition_adapter_contract():
    """Verify RecognitionBackend contract, empty frames, and reset."""
    backend = build_recognition_backend()
    assert isinstance(backend, SLTRecognitionBackend)

    # Empty observations should return empty confirmed list
    res = backend.process([], timestamp_ms=100)
    assert isinstance(res, list)
    assert len(res) == 0

    # With dummy observation
    dummy_norm = np.zeros((21, 3), dtype=np.float32)
    obs = HandObservation(
        landmarks_norm=dummy_norm,
        landmarks_world=None,
        handedness="Right",
        score=0.9
    )

    res2 = backend.process([obs], timestamp_ms=200)
    assert isinstance(res2, list)

    backend.reset()
    assert len(backend._new_events) == 0
