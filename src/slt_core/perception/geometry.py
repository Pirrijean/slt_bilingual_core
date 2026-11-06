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


# ---------------------------------------------------------------------------
# Section 2.4 Independent 2D and 3D Geometry Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Point2D:
    """2D Cartesian point in image pixel coordinates."""

    x_px: float
    y_px: float


@dataclass(frozen=True, slots=True)
class BoundingBox2D:
    """2D Bounding box in image pixel coordinates."""

    x_min_px: float
    y_min_px: float
    x_max_px: float
    y_max_px: float


@dataclass(frozen=True, slots=True)
class HandGeometry2D:
    """Strict 2D image-coordinate geometry for bounding boxes, center, and finger angles."""

    tracking_id: int | None
    bounding_box: BoundingBox2D
    palm_center: Point2D
    palm_width_px: float
    relative_landmarks: tuple[Point2D, ...]
    finger_angles_deg: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class Point3D:
    """3D point in anatomical world coordinates."""

    x_m: float
    y_m: float
    z_m: float


@dataclass(frozen=True, slots=True)
class HandGeometry3D:
    """Strict 3D world-coordinate anatomical geometry for joint angles and relative configuration."""

    tracking_id: int | None
    world_landmarks: tuple[Point3D, ...]
    joint_angles_deg: tuple[tuple[str, float], ...] = ()


def compute_hand_geometry_2d(
    observation: HandObservation,
    width: int,
    height: int,
) -> HandGeometry2D:
    """Compute 2D image-coordinate geometry scaled to actual pixel resolution."""
    if width <= 0 or height <= 0:
        raise GeometryError("Image width and height must be positive integers.")
    lms = observation.landmarks
    if len(lms) != 21:
        raise GeometryError(f"Expected 21 landmarks, got {len(lms)}.")

    points_px = [Point2D(x_px=lm.x * width, y_px=lm.y * height) for lm in lms]
    xs = [p.x_px for p in points_px]
    ys = [p.y_px for p in points_px]

    bbox = BoundingBox2D(
        x_min_px=min(xs),
        y_min_px=min(ys),
        x_max_px=max(xs),
        y_max_px=max(ys),
    )

    index_mcp = points_px[5]
    pinky_mcp = points_px[17]
    palm_width_px = sqrt((index_mcp.x_px - pinky_mcp.x_px) ** 2 + (index_mcp.y_px - pinky_mcp.y_px) ** 2)
    if palm_width_px < 1e-5:
        raise GeometryError("Degenerate palm width in 2D geometry.")

    wrist = points_px[0]
    middle_mcp = points_px[9]
    palm_center = Point2D(
        x_px=(wrist.x_px + middle_mcp.x_px) * 0.5,
        y_px=(wrist.y_px + middle_mcp.y_px) * 0.5,
    )

    scale = 1.0 / palm_width_px
    rel_lms = tuple(
        Point2D(
            x_px=(p.x_px - wrist.x_px) * scale,
            y_px=(p.y_px - wrist.y_px) * scale,
        )
        for p in points_px
    )

    # Basic finger angles in 2D
    angles = []
    finger_indices = [
        ("thumb", 1, 2, 4),
        ("index", 5, 6, 8),
        ("middle", 9, 10, 12),
        ("ring", 13, 14, 16),
        ("pinky", 17, 18, 20),
    ]
    for name, p1_idx, v_idx, p2_idx in finger_indices:
        try:
            ang = angle_degrees(lms[p1_idx], lms[v_idx], lms[p2_idx])
            angles.append((name, ang))
        except GeometryError:
            angles.append((name, 0.0))

    return HandGeometry2D(
        tracking_id=observation.tracking_id,
        bounding_box=bbox,
        palm_center=palm_center,
        palm_width_px=palm_width_px,
        relative_landmarks=rel_lms,
        finger_angles_deg=tuple(angles),
    )


def compute_hand_geometry_3d(
    observation: HandObservation,
    world_landmarks: tuple[Landmark, ...] | None = None,
) -> HandGeometry3D:
    """Compute 3D world geometry using anatomical world coordinates."""
    lms = world_landmarks if world_landmarks is not None else observation.landmarks
    if len(lms) != 21:
        raise GeometryError(f"Expected 21 landmarks, got {len(lms)}.")

    points_3d = tuple(Point3D(x_m=lm.x, y_m=lm.y, z_m=lm.z) for lm in lms)

    angles = []
    finger_indices = [
        ("thumb_mcp", 1, 2, 3),
        ("thumb_ip", 2, 3, 4),
        ("index_mcp", 0, 5, 6),
        ("index_pip", 5, 6, 7),
        ("middle_mcp", 0, 9, 10),
        ("middle_pip", 9, 10, 11),
        ("ring_mcp", 0, 13, 14),
        ("ring_pip", 13, 14, 15),
        ("pinky_mcp", 0, 17, 18),
        ("pinky_pip", 17, 18, 19),
    ]
    for name, p1_idx, v_idx, p2_idx in finger_indices:
        try:
            ang = angle_degrees(lms[p1_idx], lms[v_idx], lms[p2_idx])
            angles.append((name, ang))
        except GeometryError:
            angles.append((name, 0.0))

    return HandGeometry3D(
        tracking_id=observation.tracking_id,
        world_landmarks=points_3d,
        joint_angles_deg=tuple(angles),
    )
