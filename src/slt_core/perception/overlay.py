"""SLT Hand Landmark and Tracking Visualization Overlay."""
from __future__ import annotations

import cv2
import numpy as np

from slt_core.domain import PerceptionFrame
from slt_core.perception.errors import InvalidFrameError

HAND_CONNECTIONS = (
    # Palm
    (0, 1), (0, 5), (5, 9), (9, 13), (13, 17), (0, 17),
    # Thumb
    (1, 2), (2, 3), (3, 4),
    # Index
    (5, 6), (6, 7), (7, 8),
    # Middle
    (9, 10), (10, 11), (11, 12),
    # Ring
    (13, 14), (14, 15), (15, 16),
    # Pinky
    (17, 18), (18, 19), (19, 20),
)


def draw_hand_overlay(
    image: np.ndarray,
    perception: PerceptionFrame,
) -> np.ndarray:
    """
    Draw 21 landmarks, skeletal connections, bounding box, handedness,
    and tracking ID on a copy of the input image.
    Never alters the input array in-place.
    """
    if not isinstance(image, np.ndarray) or image.ndim != 3 or image.shape[2] != 3:
        raise InvalidFrameError("Overlay requires a 3-channel numpy ndarray.")

    display = image.copy()
    h, w = display.shape[:2]

    # Theme colors in BGR format
    color_bone = (176, 191, 66)    # Teal accent
    color_joint = (220, 240, 100)  # Light mint
    color_bbox = (80, 180, 240)    # Warm gold/amber
    color_text = (255, 255, 255)   # White

    for hand in perception.hands:
        pts = [
            (int(np.clip(lm.x * w, 0, w - 1)), int(np.clip(lm.y * h, 0, h - 1)))
            for lm in hand.landmarks
        ]

        # Draw skeletal connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            cv2.line(display, pts[start_idx], pts[end_idx], color_bone, 2, cv2.LINE_AA)

        # Draw anatomical landmark joints
        for pt in pts:
            cv2.circle(display, pt, 4, color_joint, -1, cv2.LINE_AA)

        # Draw bounding box
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        x_min, x_max = max(0, min(xs) - 10), min(w - 1, max(xs) + 10)
        y_min, y_max = max(0, min(ys) - 10), min(h - 1, max(ys) + 10)
        cv2.rectangle(display, (x_min, y_min), (x_max, y_max), color_bbox, 1, cv2.LINE_AA)

        # Draw label (Tracking ID + Handedness)
        label_parts = []
        if hand.tracking_id is not None:
            label_parts.append(f"ID:{hand.tracking_id}")
        label_parts.append(str(hand.handedness.value).upper())
        if hand.handedness_score is not None:
            label_parts.append(f"{hand.handedness_score:.0%}")
        label = " | ".join(label_parts)

        cv2.putText(
            display,
            label,
            (x_min, max(20, y_min - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color_text,
            1,
            cv2.LINE_AA,
        )

    return display
