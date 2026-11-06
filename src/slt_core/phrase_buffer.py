"""SLT Core Phrase Buffer."""
from __future__ import annotations

from collections.abc import Sequence

from slt_core.domain import SignEvent
from slt_core.errors import EventOrderError, ValidationError


class PhraseBuffer:
    """
    Maintains an ordered, deduplicated sequence of confirmed SignEvents.
    Enforces strict profile isolation and temporal monotonicity.
    """

    def __init__(self) -> None:
        self._events: list[SignEvent] = []
        self._event_ids: set[str] = set()
        self._profile_id: str | None = None

    @property
    def events(self) -> tuple[SignEvent, ...]:
        """Return the confirmed events in temporal order."""
        return tuple(self._events)

    @property
    def profile_id(self) -> str | None:
        """The language profile of the active phrase, or None if buffer is empty."""
        return self._profile_id

    def append(self, event: SignEvent) -> bool:
        """
        Append a SignEvent to the phrase.

        Returns True if the event was added, or False if it was a duplicate event_id.
        Raises ValidationError if mixing different language profiles.
        Raises EventOrderError if start_ns is strictly less than the previous event's start_ns.
        """
        if event.event_id in self._event_ids:
            return False

        if self._profile_id is None:
            self._profile_id = event.profile_id
        elif self._profile_id != event.profile_id:
            raise ValidationError(
                f"PhraseBuffer cannot mix profiles: active '{self._profile_id}' vs new '{event.profile_id}'."
            )

        if self._events:
            last_event = self._events[-1]
            if event.start_ns < last_event.start_ns:
                raise EventOrderError(
                    f"Event start_ns ({event.start_ns}) cannot precede previous event start_ns ({last_event.start_ns})."
                )

        self._events.append(event)
        self._event_ids.add(event.event_id)
        return True

    def append_many(self, events: Sequence[SignEvent]) -> int:
        """Append multiple events in sequence. Returns the count of newly added events."""
        added = 0
        for event in events:
            if self.append(event):
                added += 1
        return added

    def undo(self) -> SignEvent | None:
        """Remove and return the most recently appended event, or None if empty."""
        if not self._events:
            return None
        event = self._events.pop()
        self._event_ids.remove(event.event_id)
        if not self._events:
            self._profile_id = None
        return event

    def clear(self) -> None:
        """Clear all events and reset the profile lock."""
        self._events.clear()
        self._event_ids.clear()
        self._profile_id = None

    def __len__(self) -> int:
        return len(self._events)
