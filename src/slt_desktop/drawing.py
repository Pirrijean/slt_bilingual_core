#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Clean Anatomical Visualization Module.
Renders minimalist, brand-consistent skeletal overlays for Mode B (Demonstration Mode).
"""
from typing import List, Tuple
import cv2
import numpy as np

from slt_desktop.hand_landmarker import HandObservation

# Brand Palette (BGR format for OpenCV)
COLOR_TEAL_BGR: Tuple[int, int, int] = (176, 191, 66)    # Hex #42BFB0 (Teal Accent)
COLOR_WHITE_BGR: Tuple[int, int, int] = (255, 255, 255)  # Hex #FFFFFF (Joint Center)
COLOR_SLATE_BGR: Tuple[int, int, int] = (48, 37, 30)     # Hex #1E2530 (Knuckle background)
COLOR_MINT_BGR: Tuple[int, int, int] = (191, 212, 45)    # Hex #2DD4BF (Fingertip glow)

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

FINGERTIP_INDICES = {4, 8, 12, 16, 20}


def draw_hand_landmarks(
    frame: np.ndarray,
    observations: List[HandObservation],
    line_thickness: int = 2,
    joint_radius: int = 4
) -> np.ndarray:
    """
    Renders clean, professional anatomical skeleton overlays on the frame.
    Used exclusively in Mode B (Demonstration Mode).
    """
    if not observations:
        return frame

    out = frame.copy()
    h, w = out.shape[:2]

    for obs in observations:
        pts = obs.landmarks_norm
        px_coords = []
        for i in range(21):
            cx = int(np.clip(pts[i, 0] * w, 0, w - 1))
            cy = int(np.clip(pts[i, 1] * h, 0, h - 1))
            px_coords.append((cx, cy))

        # 1. Draw Bone Connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            pt1 = px_coords[start_idx]
            pt2 = px_coords[end_idx]
            cv2.line(out, pt1, pt2, COLOR_TEAL_BGR, line_thickness, cv2.LINE_AA)

        # 2. Draw Anatomical Joints
        for i, pt in enumerate(px_coords):
            if i in FINGERTIP_INDICES:
                # Fingertips highlighted with mint accent
                cv2.circle(out, pt, joint_radius + 2, COLOR_MINT_BGR, -1, cv2.LINE_AA)
                cv2.circle(out, pt, joint_radius - 1, COLOR_WHITE_BGR, -1, cv2.LINE_AA)
            elif i == 0:
                # Wrist base landmark
                cv2.circle(out, pt, joint_radius + 1, COLOR_SLATE_BGR, -1, cv2.LINE_AA)
                cv2.circle(out, pt, joint_radius, COLOR_TEAL_BGR, -1, cv2.LINE_AA)
            else:
                # Knuckles and phalangeal joints
                cv2.circle(out, pt, joint_radius, COLOR_TEAL_BGR, -1, cv2.LINE_AA)
                cv2.circle(out, pt, max(1, joint_radius - 2), COLOR_WHITE_BGR, -1, cv2.LINE_AA)

        # 3. Handedness Pill / Badge near wrist
        wrist_pt = px_coords[0]
        badge_text = f"{'D' if obs.handedness == 'Right' else 'I'}"
        badge_pos = (max(10, wrist_pt[0] - 14), min(h - 10, wrist_pt[1] + 24))
        cv2.circle(out, (badge_pos[0] + 6, badge_pos[1] - 4), 10, COLOR_SLATE_BGR, -1, cv2.LINE_AA)
        cv2.circle(out, (badge_pos[0] + 6, badge_pos[1] - 4), 10, COLOR_TEAL_BGR, 1, cv2.LINE_AA)
        cv2.putText(
            out,
            badge_text,
            (badge_pos[0] + 2, badge_pos[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            COLOR_WHITE_BGR,
            1,
            cv2.LINE_AA
        )

    return out
