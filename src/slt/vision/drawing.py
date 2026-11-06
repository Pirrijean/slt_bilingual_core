"""Visualization and landmark drawing utilities for SLT."""
from __future__ import annotations
import cv2
import numpy as np

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),           # Thumb
    (0, 5), (5, 6), (6, 7), (7, 8),           # Index
    (5, 9), (9, 10), (10, 11), (11, 12),      # Middle
    (9, 13), (13, 14), (14, 15), (15, 16),    # Ring
    (13, 17), (17, 18), (18, 19), (19, 20),   # Pinky
    (0, 17)                                    # Palm base
]

PALM_POINTS = {0, 1, 5, 9, 13, 17}
FINGER_TIPS = {4, 8, 12, 16, 20}

def draw_hand_landmarks(
    frame: np.ndarray,
    landmarks_norm: np.ndarray,
    handedness: str = "Right",
    highlight_tips: bool = True
) -> np.ndarray:
    """Draw anatomical skeleton and joints on an OpenCV BGR frame."""
    h, w = frame.shape[:2]
    # Colors: teal/green for Right, cyan/blue for Left
    line_color = (180, 220, 70) if handedness == "Right" else (240, 160, 60) # BGR
    joint_color = (255, 255, 255)
    tip_color = (60, 240, 210)

    px_pts = []
    for lm in landmarks_norm:
        px = int(np.clip(lm[0] * w, 0, w - 1))
        py = int(np.clip(lm[1] * h, 0, h - 1))
        px_pts.append((px, py))

    # Draw connection bones
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, px_pts[start], px_pts[end], line_color, 2, cv2.LINE_AA)

    # Draw landmark joints
    for idx, pt in enumerate(px_pts):
        if idx in FINGER_TIPS and highlight_tips:
            cv2.circle(frame, pt, 5, tip_color, -1, cv2.LINE_AA)
            cv2.circle(frame, pt, 7, line_color, 1, cv2.LINE_AA)
        elif idx in PALM_POINTS:
            cv2.circle(frame, pt, 4, joint_color, -1, cv2.LINE_AA)
        else:
            cv2.circle(frame, pt, 3, joint_color, -1, cv2.LINE_AA)

    return frame
