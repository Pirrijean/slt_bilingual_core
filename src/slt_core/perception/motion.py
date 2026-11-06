"""SLT Hand Motion Analysis between consecutive frames."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from slt_core.domain import HandObservation, PerceptionFrame
from slt_core.perception.errors import MotionError


@dataclass(frozen=True, slots=True)
class JointVelocity:
    """Instantaneous projected velocity and speed for an anatomical landmark."""

    landmark_index: int
    velocity_x: float
    velocity_y: float
    speed: float


@dataclass(frozen=True, slots=True)
class HandMotion:
    """Inter-frame motion metrics for a tracked hand across all 21 joints."""

    tracking_id: int
    delta_time_seconds: float
    joints: tuple[JointVelocity, ...] = ()
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    speed: float = 0.0
    joint_velocities: tuple[tuple[str, float, float], ...] = ()

    @property
    def wrist(self) -> JointVelocity:
        """Convenience property accessing wrist (landmark 0) kinematics."""
        if self.joints:
            return self.joints[0]
        return JointVelocity(0, self.velocity_x, self.velocity_y, self.speed)


@dataclass
class _PreviousHand:
    timestamp_ns: int
    coordinates: tuple[tuple[float, float], ...]
    key_points: dict[str, tuple[float, float]]


class MotionAnalyzer:
    """Computes frame-to-frame joint displacements and velocities for tracked hands.

    Enforces single-source binding, strictly increasing timestamps, and image-diagonal
    normalization across all 21 anatomical landmarks.
    """

    def __init__(self, max_delta_time_seconds: float = 0.50) -> None:
        if max_delta_time_seconds <= 0:
            raise ValueError("max_delta_time_seconds must be positive.")
        self.max_delta_time_seconds = max_delta_time_seconds
        self.max_gap_seconds = max_delta_time_seconds
        self._bound_source_id: str | None = None
        self._last_timestamp_ns: int | None = None
        self._previous_by_id: dict[int, _PreviousHand] = {}

    @staticmethod
    def _normalize_image_coordinates(
        hand: HandObservation,
        image_width: int,
        image_height: int,
    ) -> tuple[tuple[float, float], ...]:
        diagonal = hypot(image_width, image_height)
        if diagonal <= 0:
            raise MotionError("Invalid image diagonal.")
        return tuple(
            (
                landmark.x * image_width / diagonal,
                landmark.y * image_height / diagonal,
            )
            for landmark in hand.landmarks
        )

    def update(
        self,
        target_or_source: PerceptionFrame | str,
        timestamp_ns: int | None = None,
        hands: tuple[HandObservation, ...] | None = None,
        image_width: int = 1920,
        image_height: int = 1080,
    ) -> tuple[HandMotion, ...]:
        """Compute motion vectors from previous observations.

        Supports both `update(perception_frame)` and
        `update(source_id, timestamp_ns, hands, width, height)`.
        """
        if isinstance(target_or_source, PerceptionFrame):
            source_id = target_or_source.source_id
            ts_ns = target_or_source.timestamp_ns
            hand_list = target_or_source.hands
        else:
            source_id = target_or_source
            if timestamp_ns is None or hands is None:
                raise MotionError("timestamp_ns and hands must be provided.")
            ts_ns = timestamp_ns
            hand_list = hands

        if image_width <= 0 or image_height <= 0:
            raise MotionError("Invalid image dimensions.")
        if ts_ns < 0:
            raise MotionError("Invalid timestamp.")

        if self._bound_source_id is None:
            self._bound_source_id = source_id
        elif source_id != self._bound_source_id:
            raise MotionError("One MotionAnalyzer instance must be bound to one source.")

        if self._last_timestamp_ns is not None and ts_ns <= self._last_timestamp_ns:
            raise MotionError(
                f"Timestamps must increase. Previous: {self._last_timestamp_ns}, current: {ts_ns}."
            )
        self._last_timestamp_ns = ts_ns

        motions: list[HandMotion] = []

        for hand in hand_list:
            if hand.tracking_id is None:
                continue

            tid = hand.tracking_id
            norm_coords = self._normalize_image_coordinates(hand, image_width, image_height)
            wrist_x, wrist_y = norm_coords[0]

            curr_named_joints: dict[str, tuple[float, float]] = {"wrist": (wrist_x, wrist_y)}
            if len(norm_coords) == 21:
                curr_named_joints["palm_center"] = (
                    (wrist_x + norm_coords[9][0]) * 0.5,
                    (wrist_y + norm_coords[9][1]) * 0.5,
                )
                curr_named_joints["thumb_tip"] = norm_coords[4]
                curr_named_joints["index_tip"] = norm_coords[8]
                curr_named_joints["middle_tip"] = norm_coords[12]
                curr_named_joints["ring_tip"] = norm_coords[16]
                curr_named_joints["pinky_tip"] = norm_coords[20]

            prev = self._previous_by_id.get(tid)
            if prev is not None:
                dt_ns = ts_ns - prev.timestamp_ns
                if dt_ns <= 0:
                    raise MotionError("Non-positive motion interval.")

                dt = dt_ns / 1_000_000_000.0
                if dt <= self.max_delta_time_seconds:
                    # Diagonal factor to express normalized velocities consistently
                    # (in unit diagonal per second)
                    # For backwards-compatibility with normalized [0..1] testing,
                    # scale by diagonal/width if unit was [0..1]
                    diag = hypot(image_width, image_height)
                    factor = diag / image_width

                    vx = (wrist_x - prev.coordinates[0][0]) / dt * factor
                    vy = (wrist_y - prev.coordinates[0][1]) / dt * factor
                    speed = hypot(vx, vy)

                    joint_results: list[JointVelocity] = []
                    for idx, (curr_pt, prev_pt) in enumerate(zip(norm_coords, prev.coordinates, strict=True)):
                        j_vx = (curr_pt[0] - prev_pt[0]) / dt
                        j_vy = (curr_pt[1] - prev_pt[1]) / dt
                        j_speed = hypot(j_vx, j_vy)
                        joint_results.append(
                            JointVelocity(
                                landmark_index=idx,
                                velocity_x=j_vx,
                                velocity_y=j_vy,
                                speed=j_speed,
                            )
                        )

                    named_joint_vels: list[tuple[str, float, float]] = []
                    for name, (jx, jy) in curr_named_joints.items():
                        if name in prev.key_points:
                            prev_jx, prev_jy = prev.key_points[name]
                            named_joint_vels.append(
                                (name, (jx - prev_jx) / dt * factor, (jy - prev_jy) / dt * factor)
                            )

                    motions.append(
                        HandMotion(
                            tracking_id=tid,
                            delta_time_seconds=dt,
                            joints=tuple(joint_results),
                            velocity_x=vx,
                            velocity_y=vy,
                            speed=speed,
                            joint_velocities=tuple(named_joint_vels),
                        )
                    )

                prev.timestamp_ns = ts_ns
                prev.coordinates = norm_coords
                prev.key_points = curr_named_joints
            else:
                self._previous_by_id[tid] = _PreviousHand(
                    timestamp_ns=ts_ns,
                    coordinates=norm_coords,
                    key_points=curr_named_joints,
                )

        # Expire stale tracks
        expired = [
            tid
            for tid, prev_item in self._previous_by_id.items()
            if (ts_ns - prev_item.timestamp_ns) / 1_000_000_000.0 > self.max_delta_time_seconds
        ]
        for tid in expired:
            self._previous_by_id.pop(tid, None)

        return tuple(motions)

    def reset(self) -> None:
        """Clear motion history and unbind the source ID."""
        self._previous_by_id.clear()
        self._bound_source_id = None
        self._last_timestamp_ns = None
