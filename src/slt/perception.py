#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Anatomical Perception Module.
Encapsulates MediaPipe Tasks HandLandmarker and provides anatomical skeleton visualization.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging
import cv2
import numpy as np

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from slt.utils.paths import HAND_LANDMARKER_MODEL

logger = logging.getLogger("slt.perception")

# Anatomical Hand Skeleton Connections (21 Landmarks)
HAND_CONNECTIONS = [
    # Thumb
    (0, 1), (1, 2), (2, 3), (3, 4),
    # Index
    (0, 5), (5, 6), (6, 7), (7, 8),
    # Middle
    (0, 9), (9, 10), (10, 11), (11, 12),
    # Ring
    (0, 13), (13, 14), (14, 15), (15, 16),
    # Pinky
    (0, 17), (17, 18), (18, 19), (19, 20),
    # Palm transverse knuckles
    (5, 9), (9, 13), (13, 17)
]

@dataclass
class DetectedHand:
    """Represents a single detected hand in a frame."""
    landmarks_norm: np.ndarray        # Shape (21, 3): x, y, z in [0, 1]
    landmarks_world: Optional[np.ndarray]  # Shape (21, 3): metric 3D coordinates
    handedness: str                   # "Left" or "Right"
    score: float                      # Detection confidence

@dataclass
class PerceptionResult:
    """Consolidated perception result for a video frame."""
    hands: List[DetectedHand]
    inference_time_ms: float
    num_hands: int

class HandDetector:
    """
    High-level anatomical perception provider using MediaPipe Tasks HandLandmarker.
    Operates in IMAGE mode for robust, decoupled frame processing.
    """
    def __init__(self, model_path: Optional[str] = None, num_hands: int = 2, min_confidence: float = 0.5):
        self.model_path = str(model_path or HAND_LANDMARKER_MODEL)
        self.num_hands = num_hands
        self.min_confidence = min_confidence
        self._landmarker = None
        self._init_landmarker()

    def _init_landmarker(self):
        try:
            base_options = python.BaseOptions(model_asset_path=self.model_path)
            options = vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.IMAGE,
                num_hands=self.num_hands,
                min_hand_detection_confidence=self.min_confidence,
                min_hand_presence_confidence=self.min_confidence,
                min_tracking_confidence=self.min_confidence
            )
            self._landmarker = vision.HandLandmarker.create_from_options(options)
            logger.info("MediaPipe HandLandmarker initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MediaPipe HandLandmarker: {e}")
            raise

    def detect(self, frame_bgr: np.ndarray) -> PerceptionResult:
        """Process a BGR frame and return detected hand landmarks."""
        import time
        t0 = time.perf_counter()
        
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        
        detection = self._landmarker.detect(mp_image)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        detected_hands = []
        if detection and detection.hand_landmarks:
            for idx, hand_lms in enumerate(detection.hand_landmarks):
                coords = np.array([[lm.x, lm.y, lm.z] for lm in hand_lms], dtype=np.float32)
                
                handedness_label = "Right"
                score = 1.0
                if detection.handedness and idx < len(detection.handedness):
                    cat = detection.handedness[idx][0]
                    handedness_label = cat.category_name
                    score = cat.score

                world_coords = None
                if detection.hand_world_landmarks and idx < len(detection.hand_world_landmarks):
                    world_coords = np.array(
                        [[lm.x, lm.y, lm.z] for lm in detection.hand_world_landmarks[idx]],
                        dtype=np.float32
                    )

                detected_hands.append(DetectedHand(
                    landmarks_norm=coords,
                    landmarks_world=world_coords,
                    handedness=handedness_label,
                    score=score
                ))

        return PerceptionResult(
            hands=detected_hands,
            inference_time_ms=latency_ms,
            num_hands=len(detected_hands)
        )

    def close(self):
        if self._landmarker:
            self._landmarker.close()
            self._landmarker = None


def draw_hand_skeleton(image: np.ndarray, landmarks_norm: np.ndarray, color_teal=(176, 191, 66), radius: int = 3) -> np.ndarray:
    """
    Draw clean anatomical hand landmarks and bones on a BGR image.
    Uses SLT signature Teal (BGR: 176, 191, 66 -> Hex #42BFB0).
    """
    h, w = image.shape[:2]
    pts = [(int(p[0] * w), int(p[1] * h)) for p in landmarks_norm]

    # Draw bone connections
    for start_idx, end_idx in HAND_CONNECTIONS:
        pt1 = pts[start_idx]
        pt2 = pts[end_idx]
        cv2.line(image, pt1, pt2, color_teal, 2, cv2.LINE_AA)

    # Draw joint nodes
    for idx, (x, y) in enumerate(pts):
        # Emphasize fingertips
        if idx in (4, 8, 12, 16, 20):
            cv2.circle(image, (x, y), radius + 2, (243, 242, 236), -1, cv2.LINE_AA)
            cv2.circle(image, (x, y), radius + 2, color_teal, 1, cv2.LINE_AA)
        else:
            cv2.circle(image, (x, y), radius, color_teal, -1, cv2.LINE_AA)

    return image
