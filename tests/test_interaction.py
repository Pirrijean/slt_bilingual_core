import pytest
import time
from slt.interaction import SLTInteractionEngine, InteractionState, SignEvent

def test_interaction_engine_initial_state():
    engine = SLTInteractionEngine(window_size=5, quorum_count=3, min_hold_seconds=0.05)
    assert engine.state == InteractionState.IDLE
    assert len(engine.get_timeline()) == 0

def test_interaction_tracking_and_candidate():
    engine = SLTInteractionEngine(window_size=5, quorum_count=3, min_hold_seconds=0.05)
    
    # Hand detected, but no sign yet
    state = engine.process_frame(has_hands=True, raw_prediction="_NADA_", confidence=0.0, is_valid=False)
    assert state == InteractionState.TRACKING

    # Sign appears (frame 1)
    state = engine.process_frame(has_hands=True, raw_prediction="HOLA", confidence=0.9, is_valid=True)
    # Still tracking or moving to candidate
    assert state in (InteractionState.TRACKING, InteractionState.CANDIDATE)

    # Sign repeats (frame 2) -> should become CANDIDATE
    state = engine.process_frame(has_hands=True, raw_prediction="HOLA", confidence=0.9, is_valid=True)
    assert state == InteractionState.CANDIDATE

def test_interaction_confirmation_and_timeline():
    engine = SLTInteractionEngine(window_size=5, quorum_count=3, min_hold_seconds=0.01)
    confirmed_events = []
    engine.sign_confirmed.connect(lambda ev: confirmed_events.append(ev))

    # Feed 3 matching frames with a small time gap
    engine.process_frame(has_hands=True, raw_prediction="AGUA", confidence=0.95, is_valid=True)
    engine.process_frame(has_hands=True, raw_prediction="AGUA", confidence=0.95, is_valid=True)
    time.sleep(0.02)
    state = engine.process_frame(has_hands=True, raw_prediction="AGUA", confidence=0.95, is_valid=True)

    assert state in (InteractionState.CONFIRMED, InteractionState.WAITING_RELEASE)
    assert len(confirmed_events) == 1
    assert confirmed_events[0].label == "AGUA"
    assert len(engine.get_timeline()) == 1

    # While holding in WAITING_RELEASE, duplicate emissions are suppressed
    engine.process_frame(has_hands=True, raw_prediction="AGUA", confidence=0.95, is_valid=True)
    assert len(confirmed_events) == 1

def test_timeline_operations():
    engine = SLTInteractionEngine()
    ev1 = SignEvent("id1", "YO", 0.0, 0.5, 0.95)
    ev2 = SignEvent("id2", "QUERER", 0.6, 1.2, 0.92)
    engine._timeline = [ev1, ev2]

    assert len(engine.get_timeline()) == 2
    engine.remove_event("id1")
    assert len(engine.get_timeline()) == 1
    assert engine.get_timeline()[0].label == "QUERER"

    engine.clear_timeline()
    assert len(engine.get_timeline()) == 0
