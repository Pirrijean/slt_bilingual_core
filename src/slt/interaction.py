#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Interaction Engine Module.
Implements the temporal state machine, SignEvent generation, and Sign Timeline management.
Inspired by human-machine interface state transitions (AutoNav, CC BY 4.0).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Deque
from collections import deque
import time
import uuid
import logging
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("slt.interaction")

class InteractionState(Enum):
    """Discrete states of the temporal interaction engine."""
    IDLE = "idle"                        # No hand detected
    TRACKING = "tracking"                # Hand present, tracking landmarks
    CANDIDATE = "candidate"              # A potential sign is stabilizing
    CONFIRMED = "confirmed"              # Quorum reached, SignEvent emitted
    WAITING_RELEASE = "waiting_release"  # Preventing duplicate firings until hand relaxes

@dataclass(frozen=True)
class SignEvent:
    """Immutable representation of a confirmed sign event in the interaction timeline."""
    event_id: str
    label: str
    timestamp_start: float
    timestamp_end: float
    stability: float
    handedness: str = "Right"
    event_type: str = "SIGN_CONFIRMED"

    @property
    def duration_seconds(self) -> float:
        return max(0.0, self.timestamp_end - self.timestamp_start)

    @property
    def formatted_time(self) -> str:
        """Formatted timestamp for timeline display MM:SS.s"""
        mins = int(self.timestamp_start // 60)
        secs = self.timestamp_start % 60
        return f"{mins:02d}:{secs:04.1f}"


class SLTInteractionEngine(QObject):
    """
    Finite State Machine and event dispatcher for sign interactions.
    Transforms raw per-frame predictions into temporally stable SignEvents.
    """
    sign_confirmed = Signal(SignEvent)
    state_changed = Signal(InteractionState)
    candidate_progress = Signal(str, float)  # candidate_gloss, progress_ratio [0.0, 1.0]
    timeline_updated = Signal(list)          # list of SignEvent

    def __init__(
        self,
        window_size: int = 7,
        quorum_count: int = 5,
        min_hold_seconds: float = 0.20,
        release_frames: int = 3
    ):
        super().__init__()
        self.window_size = window_size
        self.quorum_count = quorum_count
        self.min_hold_seconds = min_hold_seconds
        self.release_frames = release_frames

        self.state = InteractionState.IDLE
        self._window: Deque[str] = deque(maxlen=window_size)
        self._candidate_label: Optional[str] = None
        self._candidate_start_time: float = 0.0
        self._last_confirmed_label: Optional[str] = None
        self._release_counter: int = 0
        self._timeline: List[SignEvent] = []

    def process_frame(
        self,
        has_hands: bool,
        raw_prediction: str,
        confidence: float,
        is_valid: bool,
        handedness: str = "Right"
    ) -> InteractionState:
        """
        Process a single frame prediction through the state machine.
        Returns the current InteractionState.
        """
        now = time.time()

        # Transition to IDLE if no hands are visible
        if not has_hands:
            if self.state != InteractionState.IDLE:
                self._transition(InteractionState.IDLE)
            self._window.clear()
            self._candidate_label = None
            self._last_confirmed_label = None
            self.candidate_progress.emit("", 0.0)
            return self.state

        # Hand detected: append valid prediction or '_NADA_'
        effective_pred = raw_prediction if (is_valid and raw_prediction != "_NADA_") else "_NADA_"
        self._window.append(effective_pred)

        # Count frequencies in sliding window
        counts = {}
        for item in self._window:
            counts[item] = counts.get(item, 0) + 1

        top_pred = max(counts, key=counts.get) if counts else "_NADA_"
        top_count = counts.get(top_pred, 0)

        # State Machine Transitions
        if self.state == InteractionState.IDLE:
            self._transition(InteractionState.TRACKING)

        if self.state == InteractionState.TRACKING:
            if top_pred != "_NADA_" and top_count >= 2:
                self._candidate_label = top_pred
                self._candidate_start_time = now
                self._transition(InteractionState.CANDIDATE)

        elif self.state == InteractionState.CANDIDATE:
            if top_pred != self._candidate_label:
                # Prediction diverged
                self._candidate_label = None
                self._transition(InteractionState.TRACKING)
                self.candidate_progress.emit("", 0.0)
            else:
                progress = min(1.0, top_count / float(self.quorum_count))
                self.candidate_progress.emit(self._candidate_label, progress)
                hold_duration = now - self._candidate_start_time

                # Confirm if quorum is met and held
                if top_count >= self.quorum_count and hold_duration >= self.min_hold_seconds:
                    if self._candidate_label != self._last_confirmed_label:
                        self._emit_sign_event(
                            label=self._candidate_label,
                            start_time=self._candidate_start_time,
                            end_time=now,
                            stability=confidence,
                            handedness=handedness
                        )
                        self._last_confirmed_label = self._candidate_label
                        self._transition(InteractionState.CONFIRMED)
                        self._transition(InteractionState.WAITING_RELEASE)
                    else:
                        # Already emitted, keep waiting release
                        self._transition(InteractionState.WAITING_RELEASE)

        elif self.state == InteractionState.WAITING_RELEASE:
            self.candidate_progress.emit(self._last_confirmed_label or "", 1.0)
            # Check for release condition (posture changed or returned to neutral)
            if top_pred != self._last_confirmed_label or top_pred == "_NADA_":
                self._release_counter += 1
                if self._release_counter >= self.release_frames:
                    self._release_counter = 0
                    self._last_confirmed_label = None
                    self._transition(InteractionState.TRACKING)
                    self.candidate_progress.emit("", 0.0)
            else:
                self._release_counter = 0

        return self.state

    def _transition(self, new_state: InteractionState):
        if self.state != new_state:
            self.state = new_state
            self.state_changed.emit(self.state)

    def _emit_sign_event(self, label: str, start_time: float, end_time: float, stability: float, handedness: str):
        event = SignEvent(
            event_id=str(uuid.uuid4())[:8],
            label=label,
            timestamp_start=start_time,
            timestamp_end=end_time,
            stability=stability,
            handedness=handedness
        )
        self._timeline.append(event)
        logger.info(f"SIGN CONFIRMED: {event.label} (duration: {event.duration_seconds:.2f}s)")
        self.sign_confirmed.emit(event)
        self.timeline_updated.emit(list(self._timeline))

    def get_timeline(self) -> List[SignEvent]:
        return list(self._timeline)

    def remove_event(self, event_id: str):
        self._timeline = [e for e in self._timeline if e.event_id != event_id]
        self.timeline_updated.emit(list(self._timeline))

    def remove_last_event(self) -> Optional[SignEvent]:
        if self._timeline:
            ev = self._timeline.pop()
            self.timeline_updated.emit(list(self._timeline))
            return ev
        return None

    def clear_timeline(self):
        self._timeline.clear()
        self.timeline_updated.emit([])
        self._last_confirmed_label = None
        self._candidate_label = None
        self.candidate_progress.emit("", 0.0)
        self._transition(InteractionState.TRACKING)
