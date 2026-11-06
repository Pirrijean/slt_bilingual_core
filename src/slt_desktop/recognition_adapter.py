#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Recognition Backend Adapter.
Wraps the core 106-D geometric feature extractor, k-NN classifier, and temporal state machine.
"""
from __future__ import annotations
from typing import Protocol, List, Dict, Any, Optional
from pathlib import Path
import logging
import numpy as np

from slt_desktop.hand_landmarker import HandObservation
from slt.recognition import extract_features, SLTClassifier
from slt.interaction import SLTInteractionEngine, SignEvent

logger = logging.getLogger("slt_desktop.recognition_adapter")


class RecognitionBackend(Protocol):
    """Protocol defining the recognition adapter contract."""
    @property
    def ready(self) -> bool:
        ...

    @property
    def status_message(self) -> str:
        ...

    def process(
        self,
        observations: list[HandObservation],
        timestamp_ms: int,
    ) -> list[dict]:
        ...

    def reset(self) -> None:
        ...

    def close(self) -> None:
        ...


class RecognitionUnavailable:
    """Fallback backend when classifier weights or models are not yet loaded."""
    ready = False
    status_message = (
        "Detección anatómica activa. "
        "El clasificador de señas aún no está conectado."
    )

    def process(
        self,
        observations: list[HandObservation],
        timestamp_ms: int,
    ) -> list[dict]:
        return []

    def reset(self) -> None:
        pass

    def close(self) -> None:
        pass


class SLTRecognitionBackend:
    """
    Production recognition adapter connecting:
    1. MediaPipe HandObservation (21 3D landmarks)
    2. 106-D Invariant Geometric Extractor (`slt.recognition.extract_features`)
    3. Pure NumPy SLTClassifier (`slt.recognition.SLTClassifier`)
    4. Temporal Quorum State Machine (`slt.interaction.SLTInteractionEngine`)
    
    Implements the 3 discrete recognition states:
    - NO_HAND: MediaPipe does not detect any hand.
    - UNKNOWN: Hand present, but rejected due to high distance / ambiguity.
    - REST: Hand visible in neutral / rest posture (_NADA_).
    """
    def __init__(
        self,
        model_path: Optional[str | Path] = None,
        k: int = 5,
        window_size: int = 7,
        quorum_count: int = 5,
        min_hold_seconds: float = 0.20
    ):
        self.model_path = str(model_path) if model_path else None
        self.classifier = SLTClassifier(model_path=self.model_path, k=k)
        self.interaction = SLTInteractionEngine(
            window_size=window_size,
            quorum_count=quorum_count,
            min_hold_seconds=min_hold_seconds
        )
        self._new_events: List[Dict[str, Any]] = []
        self._is_ready = len(self.classifier.classes) > 0
        self.interaction.sign_confirmed.connect(self._on_sign_confirmed)

    @property
    def ready(self) -> bool:
        return self._is_ready

    @property
    def status_message(self) -> str:
        if self._is_ready:
            return f"Clasificador SLT activo ({len(self.classifier.classes)} clases)."
        return "Clasificador SLT no inicializado."

    def _on_sign_confirmed(self, event: SignEvent):
        """Signal handler capturing newly confirmed sign events."""
        event_dict = {
            "event_type": "SIGN_CONFIRMED",
            "label": event.label,
            "start_ms": int(round(event.timestamp_start * 1000.0)),
            "end_ms": int(round(event.timestamp_end * 1000.0)),
            "handedness": event.handedness,
            "stability": round(float(event.stability), 3)
        }
        self._new_events.append(event_dict)

    def process(
        self,
        observations: list[HandObservation],
        timestamp_ms: int
    ) -> list[dict]:
        """
        Per-frame recognition pipeline.
        Extracts 106-D features from dominant hand, predicts class, and steps FSM.
        """
        self._new_events.clear()
        t_sec = float(timestamp_ms) / 1000.0

        # State 1: NO_HAND (MediaPipe does not detect any hand)
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
        primary_hand = max(observations, key=lambda h: h.detection_score)
        landmarks = primary_hand.landmarks  # Shape (21, 3)

        try:
            feats = extract_features(landmarks)
            pred_class, confidence, is_valid = self.classifier.predict(feats)
        except Exception as e:
            logger.warning(f"Error extracting features or classifying: {e}")
            pred_class, confidence, is_valid = "_NADA_", 0.0, False

        # State 2: UNKNOWN (Hand present, but rejected) vs State 3: REST (_NADA_)
        effective_pred = pred_class if is_valid else "_NADA_"

        self.interaction.process_frame(
            has_hands=True,
            raw_prediction=effective_pred,
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

    def close(self) -> None:
        """Release any resources."""
        self.reset()


def build_recognition_backend(model_path: Optional[str | Path] = None) -> RecognitionBackend:
    """Factory creating the default production recognition backend."""
    try:
        backend = SLTRecognitionBackend(model_path=model_path)
        if backend.ready:
            return backend
        return RecognitionUnavailable()
    except Exception as e:
        logger.warning(f"Could not build production recognition backend: {e}")
        return RecognitionUnavailable()
