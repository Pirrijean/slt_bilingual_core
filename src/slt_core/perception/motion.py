"""SLT Hand Motion Analysis between consecutive frames."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from slt_core.domain import PerceptionFrame
from slt_core.perception.errors import MotionError


@dataclass(frozen=True, slots=True)
class HandMotion:
    """Inter-frame motion metrics for a tracked hand."""
    tracking_id: int
    delta_time_seconds: float
    velocity_x: float
    velocity_y: float
    speed: float
    # Multilateral joint velocities: (joint_name, velocity_x, velocity_y)
    joint_velocities: tuple[tuple[str, float, float], ...] = ()


@dataclass
class _PreviousHand:
    timestamp_ns: int
    x: float
    y: float
    key_points: dict[str, tuple[float, float]]


class MotionAnalyzer:
    """
    Computes frame-to-frame wrist displacement, velocities, and speed
    for each tracked hand across an ongoing session.
    """

    def __init__(self, max_delta_time_seconds: float = 0.5) -> None:
        self.max_delta_time_seconds = max_delta_time_seconds
        self._bound_source_id: str | None = None
        self._previous_by_id: dict[int, _PreviousHand] = {}

    def update(self, perception: PerceptionFrame) -> tuple[HandMotion, ...]:
        """Compute motion vectors from the previous observation of each hand."""
        if self._bound_source_id is None:
            self._bound_source_id = perception.source_id
        elif perception.source_id != self._bound_source_id:
            raise MotionError("One MotionAnalyzer instance must be bound to one source.")

        motions: list[HandMotion] = []

        for hand in perception.hands:
            if hand.tracking_id is None:
                continue

            tid = hand.tracking_id
            lms = hand.landmarks
            wrist = lms[0]
            curr_x = wrist.x
            curr_y = wrist.y

            # Extract key joint positions for multi-articulation kinematics
            curr_joints: dict[str, tuple[float, float]] = {
                "wrist": (curr_x, curr_y),
            }
            if len(lms) == 21:
                curr_joints["palm_center"] = (
                    (wrist.x + lms[9].x) * 0.5,
                    (wrist.y + lms[9].y) * 0.5,
                )
                curr_joints["thumb_tip"] = (lms[4].x, lms[4].y)
                curr_joints["index_tip"] = (lms[8].x, lms[8].y)
                curr_joints["middle_tip"] = (lms[12].x, lms[12].y)
                curr_joints["ring_tip"] = (lms[16].x, lms[16].y)
                curr_joints["pinky_tip"] = (lms[20].x, lms[20].y)

            prev = self._previous_by_id.get(tid)
            if prev is not None:
                dt_ns = perception.timestamp_ns - prev.timestamp_ns
                if dt_ns <= 0:
                    raise MotionError(
                        f"Timestamps must increase. Previous: {prev.timestamp_ns}, current: {perception.timestamp_ns}."
                    )

                dt = dt_ns / 1_000_000_000.0
                if dt <= self.max_delta_time_seconds:
                    vx = (curr_x - prev.x) / dt
                    vy = (curr_y - prev.y) / dt
                    speed = hypot(vx, vy)

                    joint_vels: list[tuple[str, float, float]] = []
                    for name, (jx, jy) in curr_joints.items():
                        if name in prev.key_points:
                            prev_jx, prev_jy = prev.key_points[name]
                            joint_vels.append((name, (jx - prev_jx) / dt, (jy - prev_jy) / dt))

                    motions.append(
                        HandMotion(
                            tracking_id=tid,
                            delta_time_seconds=dt,
                            velocity_x=vx,
                            velocity_y=vy,
                            speed=speed,
                            joint_velocities=tuple(joint_vels),
                        )
                    )

                prev.timestamp_ns = perception.timestamp_ns
                prev.x = curr_x
                prev.y = curr_y
                prev.key_points = curr_joints
            else:
                self._previous_by_id[tid] = _PreviousHand(
                    timestamp_ns=perception.timestamp_ns,
                    x=curr_x,
                    y=curr_y,
                    key_points=curr_joints,
                )

        return tuple(motions)

    def reset(self) -> None:
        """Clear motion history and unbind the source ID."""
        self._previous_by_id.clear()
        self._bound_source_id = None
