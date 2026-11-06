#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: MediaPipe Tasks Hand Landmarker Integration.
Provides anatomical perception running in VIDEO mode with monotonically increasing timestamps.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import logging
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np

from slt.utils.paths import HAND_LANDMARKER_MODEL

logger = logging.getLogger("slt_desktop.hand_landmarker")


@dataclass(slots=True)
class HandObservation:
    """
    Represents a single detected hand observation in a frame.
    Adheres strictly to the SLT Desktop specification while providing backward-compatible aliases.
    """
    landmarks: np.ndarray                        # Shape (21, 3): normalized coordinates [0, 1]
    world_landmarks: Optional[np.ndarray]        # Shape (21, 3): world metric coordinates
    handedness: str                              # "Left" or "Right"
    detection_score: float                       # Confidence score [0, 1]

    @property
    def landmarks_norm(self) -> np.ndarray:
        """Alias for backward compatibility."""
        return self.landmarks

    @property
    def score(self) -> float:
        """Alias for backward compatibility."""
        return self.detection_score


class SLTHandLandmarker:
    """
    Encapsulates MediaPipe Tasks Hand Landmarker in RunningMode.VIDEO.
    Guarantees monotonically increasing timestamps and returns clean HandObservation instances.
    """
    def __init__(
        self,
        model_path: str | Path | None = None,
        num_hands: int = 2,
        detection_confidence: float = 0.6,
        presence_confidence: float = 0.6,
        tracking_confidence: float = 0.6,
    ):
        self.model_path = Path(model_path or HAND_LANDMARKER_MODEL)
        self.num_hands = int(num_hands)
        self.detection_confidence = float(detection_confidence)
        self.presence_confidence = float(presence_confidence)
        self.tracking_confidence = float(tracking_confidence)
        self._landmarker: Optional[vision.HandLandmarker] = None
        self._last_timestamp_ms: int = -1
        self._initialize()

    def _initialize(self):
        resolved_path = self.model_path.resolve()
        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"No existe el modelo Hand Landmarker: {resolved_path}"
            )

        base_options = python.BaseOptions(model_asset_path=str(resolved_path))
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=self.num_hands,
            min_hand_detection_confidence=self.detection_confidence,
            min_hand_presence_confidence=self.presence_confidence,
            min_tracking_confidence=self.tracking_confidence
        )
        self._landmarker = vision.HandLandmarker.create_from_options(options)
        logger.info(f"SLTHandLandmarker initialized in VIDEO mode ({resolved_path.name}).")

    def detect(self, frame_bgr: np.ndarray, timestamp_ms: int) -> List[HandObservation]:
        """
        Process a BGR video frame and return list of HandObservation instances.
        Enforces strictly monotonic timestamp_ms required by MediaPipe Tasks VIDEO mode.
        """
        if self._landmarker is None:
            raise RuntimeError("SLTHandLandmarker is closed or not initialized.")

        # Ensure monotonically increasing timestamp
        ts = int(timestamp_ms)
        if ts <= self._last_timestamp_ms:
            ts = self._last_timestamp_ms + 1
        self._last_timestamp_ms = ts

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        result = self._landmarker.detect_for_video(mp_image, ts)
        observations: List[HandObservation] = []

        if not result or not result.hand_landmarks:
            return observations

        for idx, lms in enumerate(result.hand_landmarks):
            norm_coords = np.array([[lm.x, lm.y, lm.z] for lm in lms], dtype=np.float32)

            world_coords = None
            if result.hand_world_landmarks and idx < len(result.hand_world_landmarks):
                world_coords = np.array(
                    [[lm.x, lm.y, lm.z] for lm in result.hand_world_landmarks[idx]],
                    dtype=np.float32
                )

            handedness_label = "Right"
            score = 1.0
            if result.handedness and idx < len(result.handedness) and result.handedness[idx]:
                cat = result.handedness[idx][0]
                handedness_label = cat.category_name
                score = float(cat.score)

            observations.append(HandObservation(
                landmarks=norm_coords,
                world_landmarks=world_coords,
                handedness=handedness_label,
                detection_score=score
            ))

        return observations

    def close(self):
        """Release underlying MediaPipe C++ resources."""
        if self._landmarker is not None:
            try:
                self._landmarker.close()
            except Exception as e:
                logger.warning(f"Error closing HandLandmarker: {e}")
            finally:
                self._landmarker = None
