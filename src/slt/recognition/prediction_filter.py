"""Temporal stability filter and gesture event dispatcher."""
from __future__ import annotations
import time
from collections import deque, Counter
from enum import Enum

class FilterEvent(Enum):
    NONE = 0
    SIGN_CONFIRMED = 1
    SIGN_RELEASED = 2

class PredictionFilter:
    """
    Temporal stabilization filter:
      - Sliding window with majority voting to smooth frame-to-frame noise.
      - Requires a minimum streak of consistent votes before confirming.
      - Emits SIGN_CONFIRMED exactly once per steady gesture occurrence.
      - Emits SIGN_RELEASED when user drops gesture back to _NADA_ or rests.
      - Enforces cooldown and release barrier so single signs don't repeat infinitely.
    """
    def __init__(
        self,
        window_size: int = 8,
        minimum_votes: int = 5,
        min_hold_frames: int = 3,
        cooldown_sec: float = 0.35
    ):
        self.window_size = window_size
        self.minimum_votes = minimum_votes
        self.min_hold_frames = min_hold_frames
        self.cooldown_sec = cooldown_sec

        self.history: deque[str] = deque(maxlen=window_size)
        self.current_streak = 0
        self.candidate: str | None = None
        self.last_confirmed: str | None = None
        self.last_confirmed_time = 0.0
        self.released = True

    def update(self, raw_label: str | None, is_confident: bool = True) -> tuple[FilterEvent, str | None, float]:
        """
        Process a new frame prediction.
        Returns:
            (event, confirmed_label, stability_ratio)
        """
        now = time.monotonic()
        effective_label = raw_label if (is_confident and raw_label is not None) else "_NADA_"
        self.history.append(effective_label)

        counts = Counter(self.history)
        best_label, votes = counts.most_common(1)[0]
        stability = votes / len(self.history)

        if best_label == "_NADA_":
            self.current_streak = 0
            self.candidate = None
            if not self.released:
                self.released = True
                return FilterEvent.SIGN_RELEASED, None, stability
            return FilterEvent.NONE, None, stability

        # Track streak of candidate sign
        if best_label == self.candidate:
            self.current_streak += 1
        else:
            self.candidate = best_label
            self.current_streak = 1

        # Check confirmation condition
        if self.current_streak >= self.min_hold_frames:
            can_confirm = (
                (best_label != self.last_confirmed) or
                (self.released and (now - self.last_confirmed_time) >= self.cooldown_sec)
            )

            if can_confirm:
                self.last_confirmed = best_label
                self.last_confirmed_time = now
                self.released = False
                self.current_streak = 0
                return FilterEvent.SIGN_CONFIRMED, best_label, stability

        return FilterEvent.NONE, best_label, stability

    def reset(self):
        self.history.clear()
        self.current_streak = 0
        self.candidate = None
        self.last_confirmed = None
        self.last_confirmed_time = 0.0
        self.released = True
