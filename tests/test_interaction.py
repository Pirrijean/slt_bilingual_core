import time

import pytest

from slt.interaction import InteractionState, SignEvent, SLTInteractionEngine


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


def test_custom_video_timestamp_tracking():
    engine = SLTInteractionEngine(window_size=3, quorum_count=2, min_hold_seconds=0.1)
    confirmed = []
    engine.sign_confirmed.connect(lambda ev: confirmed.append(ev))

    # Simulate video frames with explicit timestamps:
    # Frame 1 (t=2.0s): Tracks hand
    engine.process_frame(True, "AYUDA", 0.95, True, custom_timestamp_sec=2.0)
    # Frame 2 (t=2.1s): Becomes candidate, marks start time
    engine.process_frame(True, "AYUDA", 0.95, True, custom_timestamp_sec=2.1)
    # Frame 3 (t=2.3s): Holds for 0.2s >= min_hold_seconds (0.1s) -> Confirms
    engine.process_frame(True, "AYUDA", 0.95, True, custom_timestamp_sec=2.3)

    assert len(confirmed) == 1
    ev = confirmed[0]
    assert ev.label == "AYUDA"
    assert ev.timestamp_start == 2.1
    assert pytest.approx(ev.timestamp_end, rel=1e-3) == 2.3
