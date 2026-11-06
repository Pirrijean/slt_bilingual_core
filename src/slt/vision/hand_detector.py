"""Hand detection using MediaPipe Tasks HandLandmarker."""
from __future__ import annotations
import time
from pathlib import Path
from dataclasses import dataclass
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

@dataclass
class HandDetection:
    landmarks_image: np.ndarray   # shape (21, 3), coordinates normalized to image [0, 1]
    landmarks_world: np.ndarray   # shape (21, 3), real-world 3D coordinates in meters
    handedness: str               # "Left" or "Right"
    score: float = 1.0

class HandDetector:
    def __init__(
        self,
        model_path: str | Path,
        num_hands: int = 2,
        min_hand_detection_confidence: float = 0.5,
        min_hand_presence_confidence: float = 0.5,
        min_tracking_confidence: float = 0.5,
        running_mode: vision.RunningMode = vision.RunningMode.VIDEO,
    ):
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise FileNotFoundError(f"No se encontró el modelo: {self.model_path}")

        base_options = python.BaseOptions(model_asset_path=str(self.model_path))
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=running_mode,
            num_hands=num_hands,
            min_hand_detection_confidence=min_hand_detection_confidence,
            min_hand_presence_confidence=min_hand_presence_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )
        self.running_mode = running_mode
        self.detector = vision.HandLandmarker.create_from_options(options)
        self._timestamp_ms = 0

    def detect(self, frame_bgr: np.ndarray) -> list[HandDetection]:
        """Process a BGR frame and return detected hands."""
        rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=np.ascontiguousarray(rgb_frame)
        )

        if self.running_mode == vision.RunningMode.VIDEO:
            self._timestamp_ms = max(self._timestamp_ms + 1, int(time.monotonic() * 1000))
            result = self.detector.detect_for_video(mp_image, self._timestamp_ms)
        else:
            result = self.detector.detect(mp_image)

        detections: list[HandDetection] = []
        if not result.hand_landmarks:
            return detections

        for i, landmarks in enumerate(result.hand_landmarks):
            lm_img = np.array([[lm.x, lm.y, lm.z] for lm in landmarks], dtype=np.float32)
            if result.hand_world_landmarks and i < len(result.hand_world_landmarks):
                lm_world = np.array([[lm.x, lm.y, lm.z] for lm in result.hand_world_landmarks[i]], dtype=np.float32)
            else:
                lm_world = lm_img.copy()

            handedness_str = "Right"
            score = 1.0
            if result.handedness and i < len(result.handedness):
                handedness_str = result.handedness[i][0].category_name
                score = float(result.handedness[i][0].score)

            detections.append(HandDetection(
                landmarks_image=lm_img,
                landmarks_world=lm_world,
                handedness=handedness_str,
                score=score
            ))

        return detections

    def close(self):
        try:
            self.detector.close()
        except Exception:
            pass
