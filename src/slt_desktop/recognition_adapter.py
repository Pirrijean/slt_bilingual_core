#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Recognition Backend Adapter.
Wraps the core 106-D geometric feature extractor, k-NN classifier, and temporal state machine.
"""
from typing import Protocol, List, Dict, Any, Optional
import numpy as np
import logging

from slt_desktop.hand_landmarker import HandObservation
from slt.recognition import extract_features, SLTClassifier
from slt.interaction import SLTInteractionEngine, SignEvent

logger = logging.getLogger("slt_desktop.recognition_adapter")


class RecognitionBackend(Protocol):
    """Protocol defining the recognition adapter contract."""
    def process(
        self,
        observations: List[HandObservation],
        timestamp_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Process hand observations for the current frame.
        Returns list of newly confirmed sign event dictionaries.
        """
        ...

    def reset(self) -> None:
        """Reset internal temporal buffers and state."""
        ...


class SLTRecognitionBackend:
    """
    Production recognition adapter connecting:
    1. MediaPipe HandObservation (21 3D landmarks)
    2. 106-D Invariant Geometric Extractor (`slt.recognition.extract_features`)
    3. Pure NumPy SLTClassifier (`slt.recognition.SLTClassifier`)
    4. Temporal Quorum State Machine (`slt.interaction.SLTInteractionEngine`)
    """
    def __init__(
        self,
        model_path: Optional[str] = None,
        k: int = 5,
        window_size: int = 7,
        quorum_count: int = 5,
        min_hold_seconds: float = 0.20
    ):
        self.classifier = SLTClassifier(model_path=model_path, k=k)
        self.interaction = SLTInteractionEngine(
            window_size=window_size,
            quorum_count=quorum_count,
            min_hold_seconds=min_hold_seconds
        )
        self._new_events: List[Dict[str, Any]] = []
        self.interaction.sign_confirmed.connect(self._on_sign_confirmed)

    def _on_sign_confirmed(self, event: SignEvent):
        """Signal handler capturing newly confirmed sign events."""
        event_dict = {
            "event_type": "SIGN_CONFIRMED",
            "label": event.label,
            "start_ms": int(round(event.timestamp_start * 1000.0)),
            "end_ms": int(round(event.timestamp_end * 1000.0)),
            "handedness": event.handedness,
            "stability": float(event.stability)
        }
        self._new_events.append(event_dict)

    def process(
        self,
        observations: List[HandObservation],
        timestamp_ms: int
    ) -> List[Dict[str, Any]]:
        """
        Per-frame recognition pipeline.
        Extracts 106-D features from dominant hand, predicts class, and steps FSM.
        """
        self._new_events.clear()
        t_sec = float(timestamp_ms) / 1000.0

        if not observations:
            self.interaction.process_frame(
                has_hands=False,
                raw_prediction="_NADA_",
                confidence=0.0,
                is_valid=False,
                custom_timestamp_sec=t_sec
            )
            return list(self._new_events)

        # Select primary hand (highest detection confidence score)
        primary_hand = max(observations, key=lambda h: h.score)
        landmarks = primary_hand.landmarks_norm  # Shape (21, 3)

        try:
            feats = extract_features(landmarks)
            pred_class, confidence, is_valid = self.classifier.predict(feats)
        except Exception as e:
            logger.warning(f"Error extracting features or classifying frame: {e}")
            pred_class, confidence, is_valid = "_NADA_", 0.0, False

        self.interaction.process_frame(
            has_hands=True,
            raw_prediction=pred_class,
            confidence=confidence,
            is_valid=is_valid,
            handedness=primary_hand.handedness,
            custom_timestamp_sec=t_sec
        )

        return list(self._new_events)

    def reset(self) -> None:
        """Reset state machine and buffers."""
        self._new_events.clear()
        self.interaction.clear_timeline()


def build_recognition_backend(model_path: Optional[str] = None) -> RecognitionBackend:
    """Factory creating the default production recognition backend."""
    return SLTRecognitionBackend(model_path=model_path)
