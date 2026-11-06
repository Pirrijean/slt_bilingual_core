"""Unit tests for PhraseBuffer."""
import pytest

from slt_core.domain import Handedness, ScoreSemantics, SignEvent
from slt_core.errors import EventOrderError, ValidationError
from slt_core.phrase_buffer import PhraseBuffer


def make_event(
    event_id: str,
    sign_id: str,
    start_ns: int,
    profile_id: str = "test_language",
    end_ns: int | None = None,
) -> SignEvent:
    return SignEvent(
        event_id=event_id,
        profile_id=profile_id,
        sign_id=sign_id,
        start_ns=start_ns,
        end_ns=end_ns if end_ns is not None else start_ns + 100,
        handedness=(Handedness.RIGHT,),
        score=0.9,
        score_semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
    )


def test_append_and_retrieve():
    buffer = PhraseBuffer()
    assert len(buffer) == 0
    assert buffer.profile_id is None
    assert buffer.events == ()

    ev1 = make_event("ev_1", "SIGN_A", 1000)
    assert buffer.append(ev1) is True
    assert len(buffer) == 1
    assert buffer.profile_id == "test_language"
    assert buffer.events == (ev1,)

    ev2 = make_event("ev_2", "SIGN_B", 2000)
    assert buffer.append(ev2) is True
    assert len(buffer) == 2
    assert buffer.events == (ev1, ev2)


def test_deduplication():
    buffer = PhraseBuffer()
    ev1 = make_event("ev_1", "SIGN_A", 1000)
    assert buffer.append(ev1) is True

    # Same event_id with different timestamp or sign -> rejected by ID
    duplicate = make_event("ev_1", "SIGN_DIFFERENT", 2000)
    assert buffer.append(duplicate) is False
    assert len(buffer) == 1
    assert buffer.events[0].sign_id == "SIGN_A"


def test_profile_isolation():
    buffer = PhraseBuffer()
    ev_lsc = make_event("ev_1", "SIGN_A", 1000, profile_id="lsc")
    buffer.append(ev_lsc)

    ev_asl = make_event("ev_2", "SIGN_B", 2000, profile_id="asl")
    with pytest.raises(ValidationError, match="cannot mix profiles"):
        buffer.append(ev_asl)


def test_temporal_monotonicity():
    buffer = PhraseBuffer()
    ev1 = make_event("ev_1", "SIGN_A", 2000)
    buffer.append(ev1)

    # Regressive start_ns
    ev_regressive = make_event("ev_2", "SIGN_B", 1500)
    with pytest.raises(EventOrderError, match="precede previous"):
        buffer.append(ev_regressive)

    # Simultaneous start_ns is allowed (e.g. bimanual compound signs occurring together)
    ev_simultaneous = make_event("ev_3", "SIGN_C", 2000)
    assert buffer.append(ev_simultaneous) is True


def test_append_many():
    buffer = PhraseBuffer()
    events = [
        make_event("ev_1", "SIGN_A", 1000),
        make_event("ev_1", "SIGN_A", 1000),  # duplicate
        make_event("ev_2", "SIGN_B", 2000),
    ]
    added = buffer.append_many(events)
    assert added == 2
    assert len(buffer) == 2


def test_undo():
    buffer = PhraseBuffer()
    ev1 = make_event("ev_1", "SIGN_A", 1000, profile_id="lsc")
    ev2 = make_event("ev_2", "SIGN_B", 2000, profile_id="lsc")

    buffer.append(ev1)
    buffer.append(ev2)

    removed = buffer.undo()
    assert removed == ev2
    assert len(buffer) == 1
    assert buffer.events == (ev1,)

    # Undo last event: buffer is empty and profile_id is reset
    removed_first = buffer.undo()
    assert removed_first == ev1
    assert len(buffer) == 0
    assert buffer.profile_id is None

    # Undo on empty buffer returns None
    assert buffer.undo() is None

    # We can now append an event from a different profile
    ev_asl = make_event("ev_3", "SIGN_C", 3000, profile_id="asl")
    assert buffer.append(ev_asl) is True
    assert buffer.profile_id == "asl"


def test_clear():
    buffer = PhraseBuffer()
    buffer.append(make_event("ev_1", "SIGN_A", 1000, profile_id="lsc"))
    buffer.clear()

    assert len(buffer) == 0
    assert buffer.events == ()
    assert buffer.profile_id is None
