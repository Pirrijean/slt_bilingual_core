"""SLT Hand Geometry Engine."""
from __future__ import annotations

from dataclasses import dataclass
from math import acos, degrees, sqrt
from typing import NamedTuple

from slt_core.domain import HandObservation, Landmark
from slt_core.perception.errors import GeometryError


class BoundingBox(NamedTuple):
    """2D Bounding box in normalized coordinates."""
    x_min: float
    y_min: float
    x_max: float
    y_max: float


@dataclass(frozen=True, slots=True)
class HandGeometry:
    """Anatomical geometric features extracted from a hand observation."""
    tracking_id: int | None
    bounding_box: BoundingBox
    palm_center: Landmark
    palm_width: float
    wrist_to_middle_mcp: float
    relative_landmarks: tuple[Landmark, ...]


def euclidean_distance(p1: Landmark, p2: Landmark) -> float:
    """Compute 3D Euclidean distance between two landmarks."""
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    dz = p1.z - p2.z
    return sqrt(dx * dx + dy * dy + dz * dz)


def angle_degrees(p1: Landmark, vertex: Landmark, p2: Landmark) -> float:
    """
    Calculate the joint angle in degrees formed at `vertex` between `p1` and `p2`.
    Returns a value between 0.0 and 180.0 degrees.
    """
    v1_x = p1.x - vertex.x
    v1_y = p1.y - vertex.y
    v1_z = p1.z - vertex.z

    v2_x = p2.x - vertex.x
    v2_y = p2.y - vertex.y
    v2_z = p2.z - vertex.z

    mag1 = sqrt(v1_x * v1_x + v1_y * v1_y + v1_z * v1_z)
    mag2 = sqrt(v2_x * v2_x + v2_y * v2_y + v2_z * v2_z)

    if mag1 < 1e-9 or mag2 < 1e-9:
        raise GeometryError("Cannot compute angle for coincident joint landmarks.")

    dot = v1_x * v2_x + v1_y * v2_y + v1_z * v2_z
    cos_val = max(-1.0, min(1.0, dot / (mag1 * mag2)))
    return degrees(acos(cos_val))


def compute_hand_geometry(observation: HandObservation) -> HandGeometry:
    """
    Compute spatial dimensions, palm center, palm width, finger angles,
    and palm-normalized relative coordinates for a hand observation.
    """
    lms = observation.landmarks
    if len(lms) != 21:
        raise GeometryError(f"Expected 21 landmarks, got {len(lms)}.")

    wrist = lms[0]
    index_mcp = lms[5]
    middle_mcp = lms[9]
    pinky_mcp = lms[17]

    xs = [lm.x for lm in lms]
    ys = [lm.y for lm in lms]
    bbox = BoundingBox(
        x_min=min(xs),
        y_min=min(ys),
        x_max=max(xs),
        y_max=max(ys),
    )

    palm_width = euclidean_distance(index_mcp, pinky_mcp)
    if palm_width < 1e-7:
        raise GeometryError("Palm width is zero or degenerate; cannot normalize landmarks.")

    wrist_to_middle = euclidean_distance(wrist, middle_mcp)

    palm_center = Landmark(
        x=(wrist.x + middle_mcp.x) * 0.5,
        y=(wrist.y + middle_mcp.y) * 0.5,
        z=(wrist.z + middle_mcp.z) * 0.5,
    )

    # Normalize relative to wrist and scaled by palm width
    scale = 1.0 / palm_width
    relative_lms = tuple(
        Landmark(
            x=(lm.x - wrist.x) * scale,
            y=(lm.y - wrist.y) * scale,
            z=(lm.z - wrist.z) * scale,
        )
        for lm in lms
    )

    return HandGeometry(
        tracking_id=observation.tracking_id,
        bounding_box=bbox,
        palm_center=palm_center,
        palm_width=palm_width,
        wrist_to_middle_mcp=wrist_to_middle,
        relative_landmarks=relative_lms,
    )
