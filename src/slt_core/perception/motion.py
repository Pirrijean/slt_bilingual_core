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


@dataclass
class _PreviousHand:
    timestamp_ns: int
    x: float
    y: float


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
            wrist = hand.landmarks[0]
            curr_x = wrist.x
            curr_y = wrist.y

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
                    motions.append(
                        HandMotion(
                            tracking_id=tid,
                            delta_time_seconds=dt,
                            velocity_x=vx,
                            velocity_y=vy,
                            speed=speed,
                        )
                    )

                prev.timestamp_ns = perception.timestamp_ns
                prev.x = curr_x
                prev.y = curr_y
            else:
                self._previous_by_id[tid] = _PreviousHand(
                    timestamp_ns=perception.timestamp_ns,
                    x=curr_x,
                    y=curr_y,
                )

        return tuple(motions)

    def reset(self) -> None:
        """Clear motion history and unbind the source ID."""
        self._previous_by_id.clear()
        self._bound_source_id = None
