#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Clean Anatomical Visualization Module.
Renders minimalist, brand-consistent skeletal overlays for Mode B (Demonstration Mode).
"""
from __future__ import annotations
import cv2
import numpy as np
from slt_desktop.hand_landmarker import HandObservation

# Anatomical Hand Skeleton Connections (21 Landmarks)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

# Official BGR Palette for OpenCV
TEAL = (176, 191, 66)        # Brand Teal #42BFB0
WHITE = (245, 245, 245)      # Soft White #F5F5F5
TEXT_COLOR = (235, 245, 245) # Muted Text
SLATE = (48, 37, 30)         # Dark Slate Knuckles

FINGERTIP_INDICES = {4, 8, 12, 16, 20}


def draw_hand_landmarks(
    frame: np.ndarray,
    observations: list[HandObservation],
    line_thickness: int = 2,
    joint_radius: int = 3
) -> np.ndarray:
    """
    Renders clean, professional anatomical skeleton overlays on the frame.
    Separated completely from recognition to allow toggling visual representation
    without disabling background perception.
    """
    if not observations:
        return frame

    out = frame.copy()
    height, width = out.shape[:2]

    for observation in observations:
        points = observation.landmarks
        pixel_points = []
        for x, y, _ in points:
            cx = int(np.clip(x * width, 0, width - 1))
            cy = int(np.clip(y * height, 0, height - 1))
            pixel_points.append((cx, cy))

        # 1. Draw Bone Connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            pt1 = pixel_points[start_idx]
            pt2 = pixel_points[end_idx]
            cv2.line(out, pt1, pt2, TEAL, line_thickness, cv2.LINE_AA)

        # 2. Draw Subtle Anatomical Joints
        for i, pt in enumerate(pixel_points):
            if i in FINGERTIP_INDICES:
                cv2.circle(out, pt, joint_radius + 1, TEAL, -1, cv2.LINE_AA)
                cv2.circle(out, pt, joint_radius - 1, WHITE, -1, cv2.LINE_AA)
            elif i == 0:
                cv2.circle(out, pt, joint_radius + 1, SLATE, -1, cv2.LINE_AA)
                cv2.circle(out, pt, joint_radius, TEAL, -1, cv2.LINE_AA)
            else:
                cv2.circle(out, pt, joint_radius, TEAL, -1, cv2.LINE_AA)
                cv2.circle(out, pt, max(1, joint_radius - 1), WHITE, -1, cv2.LINE_AA)

        # 3. Discreet Handedness Indicator
        wrist_pt = pixel_points[0]
        badge_text = "R" if observation.handedness == "Right" else "L"
        badge_x = max(10, wrist_pt[0] - 12)
        badge_y = min(height - 10, wrist_pt[1] + 20)
        cv2.putText(
            out,
            badge_text,
            (badge_x, badge_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            TEXT_COLOR,
            1,
            cv2.LINE_AA
        )

    return out
