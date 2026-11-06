"""MediaPipe Tasks Hand Landmarker perception backend for SLT Core."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2

from slt_core.domain import (
    FramePacket,
    Handedness,
    HandObservation,
    Landmark,
    PerceptionFrame,
)
from slt_core.perception.errors import (
    PerceptionInitializationError,
    PerceptionProcessingError,
)
from slt_core.perception.image import validate_bgr_frame
from slt_core.perception.model_assets import verify_model_asset
from slt_core.perception.tracking import HandTracker


@dataclass(frozen=True, slots=True)
class MediaPipeHandConfig:
    """Configuration options for MediaPipe Tasks Hand Landmarker."""
    max_hands: int = 2
    min_hand_detection_confidence: float = 0.5
    min_hand_presence_confidence: float = 0.5
    min_tracking_confidence: float = 0.5


def convert_mediapipe_result(result: Any) -> tuple[HandObservation, ...]:
    """
    Convert a MediaPipe HandLandmarkerResult into SLT HandObservation tuples.
    Does not assign tracking IDs (tracker assigns them subsequently).
    """
    if result is None or not getattr(result, "hand_landmarks", None):
        return ()

    hand_landmarks = result.hand_landmarks
    world_landmarks = getattr(result, "hand_world_landmarks", None) or []
    handedness_list = getattr(result, "handedness", None) or []

    observations: list[HandObservation] = []
    num_hands = len(hand_landmarks)

    for i in range(num_hands):
        lms = tuple(
            Landmark(x=float(pt.x), y=float(pt.y), z=float(pt.z))
            for pt in hand_landmarks[i]
        )

        if i < len(world_landmarks) and len(world_landmarks[i]) == 21:
            wlms = tuple(
                Landmark(x=float(pt.x), y=float(pt.y), z=float(pt.z))
                for pt in world_landmarks[i]
            )
        else:
            wlms = lms  # Fallback if world landmarks unavailable

        hand_side = Handedness.UNKNOWN
        score: float | None = None

        if i < len(handedness_list) and handedness_list[i]:
            category = handedness_list[i][0]
            cat_name = getattr(category, "category_name", "").lower()
            if cat_name == "left":
                hand_side = Handedness.LEFT
            elif cat_name == "right":
                hand_side = Handedness.RIGHT
            score = float(getattr(category, "score", 0.0))

        observations.append(
            HandObservation(
                tracking_id=None,
                handedness=hand_side,
                landmarks=lms,
                world_landmarks=wlms,
                handedness_score=score,
            )
        )

    return tuple(observations)


class MediaPipeHandPerception:
    """
    Synchronous video-mode perception backend using MediaPipe Tasks Hand Landmarker.
    Maintains dedicated state per source, tracking hands and emitting PerceptionFrames.
    """

    def __init__(
        self,
        model_path: str | Path,
        config: MediaPipeHandConfig | None = None,
        tracker: HandTracker | None = None,
        manifest_path: str | Path | None = None,
    ) -> None:
        self.model_path = Path(model_path).resolve()
        self.config = config or MediaPipeHandConfig()
        self.tracker = tracker or HandTracker()

        # Check model checksum before initializing
        self.model_sha256 = verify_model_asset(self.model_path, manifest_path)

        self._bound_source_id: str | None = None
        self._landmarker: Any | None = None
        self._mp: Any | None = None
        self._last_timestamp_ms: int = -1
        self._forced_timestamp_increments: int = 0

        self._initialize_landmarker()

    def _initialize_landmarker(self) -> None:
        try:
            import mediapipe as mp
            from mediapipe.tasks import python as mp_python
            from mediapipe.tasks.python import vision as mp_vision

            self._mp = mp
            base_options = mp_python.BaseOptions(model_asset_path=str(self.model_path))
            options = mp_vision.HandLandmarkerOptions(
                base_options=base_options,
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=self.config.max_hands,
                min_hand_detection_confidence=self.config.min_hand_detection_confidence,
                min_hand_presence_confidence=self.config.min_hand_presence_confidence,
                min_tracking_confidence=self.config.min_tracking_confidence,
            )
            self._landmarker = mp_vision.HandLandmarker.create_from_options(options)
        except Exception as exc:
            raise PerceptionInitializationError(
                f"Failed to initialize MediaPipe HandLandmarker: {exc}"
            ) from exc

    @property
    def ready(self) -> bool:
        """True if the MediaPipe landmarker is active and initialized."""
        return self._landmarker is not None

    @property
    def forced_timestamp_increments(self) -> int:
        """Total count of millisecond adjustments forced to maintain C++ monotony."""
        return self._forced_timestamp_increments

    def detect(self, packet: FramePacket) -> PerceptionFrame:
        """
        Process a FramePacket, detect hands with MediaPipe Hand Landmarker,
        update temporal tracking, and return a PerceptionFrame.
        """
        mp = self._mp
        landmarker = self._landmarker
        if mp is None or landmarker is None:
            raise PerceptionProcessingError("MediaPipe resources are unavailable.")

        if self._bound_source_id is None:
            self._bound_source_id = packet.source_id
        elif packet.source_id != self._bound_source_id:
            raise PerceptionProcessingError("One MediaPipeHandPerception instance must process one source.")

        # 1. Validate image format and memory layout
        bgr = validate_bgr_frame(packet)

        # 2. Convert BGR to RGB (MediaPipe expects RGB)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

        # 3. Compute monotonically increasing timestamp_ms for MediaPipe C++ runtime
        timestamp_ms = packet.timestamp_ns // 1_000_000
        if timestamp_ms <= self._last_timestamp_ms:
            timestamp_ms = self._last_timestamp_ms + 1
            self._forced_timestamp_increments += 1
        self._last_timestamp_ms = timestamp_ms

        # 4. Invoke MediaPipe Hand Landmarker in VIDEO mode
        try:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)
        except Exception as exc:
            raise PerceptionProcessingError(f"MediaPipe inference failed: {exc}") from exc

        # 5. Convert raw results to SLT HandObservations
        raw_observations = convert_mediapipe_result(result)

        # 6. Associate with SLT HandTracker for temporal IDs
        tracked_hands = self.tracker.update(packet.frame_index, raw_observations)

        return PerceptionFrame(
            source_id=packet.source_id,
            frame_index=packet.frame_index,
            timestamp_ns=packet.timestamp_ns,
            hands=tracked_hands,
        )

    def close(self) -> None:
        """Close MediaPipe landmarker and release underlying resources."""
        if self._landmarker is not None:
            self._landmarker.close()
            self._landmarker = None
        self.tracker.reset()
        self._bound_source_id = None
        self._last_timestamp_ms = -1
        self._forced_timestamp_increments = 0
