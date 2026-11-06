"""SLT Hand Tracker for persistent multi-frame identity assignment."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from math import hypot

from slt_core.domain import Handedness, HandObservation
from slt_core.perception.errors import TrackingError


@dataclass
class _Track:
    tracking_id: int
    center_x: float
    center_y: float
    handedness: Handedness
    last_frame_index: int


class HandTracker:
    """
    Associates hand observations across consecutive frames to maintain
    temporal tracking IDs. Uses spatial proximity and handedness consistency.
    """

    def __init__(
        self,
        max_distance: float = 0.30,
        handedness_penalty: float = 0.10,
        max_missed_frames: int = 12,
    ) -> None:
        self.max_distance = max_distance
        self.handedness_penalty = handedness_penalty
        self.max_missed_frames = max_missed_frames

        self._next_id = 1
        self._tracks: dict[int, _Track] = {}
        self._last_frame_index: int | None = None

    def update(
        self,
        frame_index: int,
        observations: Sequence[HandObservation],
    ) -> tuple[HandObservation, ...]:
        """
        Assign persistent tracking IDs to observations in the current frame.
        """
        if self._last_frame_index is not None and frame_index <= self._last_frame_index:
            raise TrackingError(
                f"Frame index must increase strictly. Previous: {self._last_frame_index}, current: {frame_index}."
            )
        self._last_frame_index = frame_index

        # 1. Prune expired tracks
        expired_ids = [
            tid
            for tid, track in self._tracks.items()
            if frame_index - track.last_frame_index > self.max_missed_frames
        ]
        for tid in expired_ids:
            del self._tracks[tid]

        if not observations:
            return ()

        # 2. Compute centers for all incoming observations
        obs_centers = [
            (
                sum(lm.x for lm in obs.landmarks) / len(obs.landmarks),
                sum(lm.y for lm in obs.landmarks) / len(obs.landmarks),
            )
            for obs in observations
        ]

        # 3. Compute cost matrix between active tracks and observations
        track_ids = list(self._tracks.keys())
        matches: dict[int, int] = {}  # obs_idx -> tracking_id
        assigned_track_ids: set[int] = set()

        if track_ids:
            # Build all (cost, track_id, obs_idx) candidates
            candidates: list[tuple[float, int, int]] = []
            for obs_idx, (cx, cy) in enumerate(obs_centers):
                obs = observations[obs_idx]
                for tid in track_ids:
                    track = self._tracks[tid]
                    dist = hypot(track.center_x - cx, track.center_y - cy)
                    penalty = 0.0
                    if (
                        track.handedness != Handedness.UNKNOWN
                        and obs.handedness != Handedness.UNKNOWN
                        and track.handedness != obs.handedness
                    ):
                        penalty = self.handedness_penalty

                    cost = dist + penalty
                    if cost <= self.max_distance:
                        candidates.append((cost, tid, obs_idx))

            # Greedy 1-to-1 matching by ascending cost
            candidates.sort(key=lambda c: c[0])
            matched_obs_indices: set[int] = set()
            for cost, tid, obs_idx in candidates:
                if tid not in assigned_track_ids and obs_idx not in matched_obs_indices:
                    matches[obs_idx] = tid
                    assigned_track_ids.add(tid)
                    matched_obs_indices.add(obs_idx)

        # 4. Assign IDs and update tracks
        tracked_observations: list[HandObservation] = []
        for obs_idx, obs in enumerate(observations):
            cx, cy = obs_centers[obs_idx]
            if obs_idx in matches:
                tid = matches[obs_idx]
                track = self._tracks[tid]
                track.center_x = cx
                track.center_y = cy
                track.last_frame_index = frame_index
                if obs.handedness != Handedness.UNKNOWN:
                    track.handedness = obs.handedness
            else:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = _Track(
                    tracking_id=tid,
                    center_x=cx,
                    center_y=cy,
                    handedness=obs.handedness,
                    last_frame_index=frame_index,
                )

            tracked_observations.append(replace(obs, tracking_id=tid))

        return tuple(tracked_observations)

    def reset(self) -> None:
        """Reset all tracking history and state."""
        self._tracks.clear()
        self._next_id = 1
        self._last_frame_index = None
