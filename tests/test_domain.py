"""Unit tests for SLT Core domain models and typed data contracts."""
import pytest

from slt_core.domain import (
    FramePacket,
    Handedness,
    HandObservation,
    Landmark,
    LanguageProfile,
    PerceptionFrame,
    RecognitionHypothesis,
    ScoreSemantics,
    SignEvent,
    TranslationOutput,
)
from slt_core.errors import ValidationError


def make_landmarks(count: int = 21) -> tuple[Landmark, ...]:
    return tuple(
        Landmark(x=float(i) / 21, y=float(i) / 21, z=0.0) for i in range(count)
    )


def test_landmark_valid():
    lm = Landmark(x=0.5, y=0.5, z=0.0)
    assert lm.x == 0.5
    assert lm.y == 0.5
    assert lm.z == 0.0


def test_landmark_non_finite_raises():
    with pytest.raises(ValidationError, match="finite"):
        Landmark(x=float("nan"), y=0.0, z=0.0)
    with pytest.raises(ValidationError, match="finite"):
        Landmark(x=0.0, y=float("inf"), z=0.0)


def test_hand_observation_valid():
    obs = HandObservation(
        tracking_id=1,
        handedness=Handedness.RIGHT,
        landmarks=make_landmarks(21),
        world_landmarks=make_landmarks(21),
        handedness_score=0.98,
    )
    assert obs.tracking_id == 1
    assert obs.handedness == Handedness.RIGHT
    assert len(obs.landmarks) == 21
    assert len(obs.world_landmarks) == 21
    assert obs.handedness_score == 0.98


def test_hand_observation_invalid():
    # Negative tracking ID
    with pytest.raises(ValidationError, match="tracking_id cannot be negative"):
        HandObservation(
            tracking_id=-1,
            handedness=Handedness.LEFT,
            landmarks=make_landmarks(21),
            world_landmarks=make_landmarks(21),
        )
    # Incorrect landmark count
    with pytest.raises(ValidationError, match="21 image landmarks"):
        HandObservation(
            tracking_id=0,
            handedness=Handedness.LEFT,
            landmarks=make_landmarks(20),
            world_landmarks=make_landmarks(21),
        )
    # Incorrect world landmark count
    with pytest.raises(ValidationError, match="21 world landmarks"):
        HandObservation(
            tracking_id=0,
            handedness=Handedness.LEFT,
            landmarks=make_landmarks(21),
            world_landmarks=make_landmarks(10),
        )
    # Invalid handedness score
    with pytest.raises(ValidationError, match="handedness_score"):
        HandObservation(
            tracking_id=0,
            handedness=Handedness.LEFT,
            landmarks=make_landmarks(21),
            world_landmarks=make_landmarks(21),
            handedness_score=1.5,
        )


def test_frame_packet_valid():
    packet = FramePacket(
        source_id="cam_0",
        frame_index=0,
        timestamp_ns=1000,
        image=None,
        pixel_format="BGR24",
        timestamp_kind="monotonic",
    )
    assert packet.source_id == "cam_0"
    assert packet.frame_index == 0
    assert packet.timestamp_ns == 1000
    assert packet.pixel_format == "BGR24"
    assert packet.timestamp_kind == "monotonic"


def test_frame_packet_invalid():
    with pytest.raises(ValidationError, match="source_id"):
        FramePacket(source_id="  ", frame_index=0, timestamp_ns=0)
    with pytest.raises(ValidationError, match="frame_index"):
        FramePacket(source_id="cam", frame_index=-1, timestamp_ns=0)
    with pytest.raises(ValidationError, match="timestamp_ns"):
        FramePacket(source_id="cam", frame_index=0, timestamp_ns=-5)
    with pytest.raises(ValidationError, match="timestamp_kind"):
        FramePacket(source_id="cam", frame_index=0, timestamp_ns=0, timestamp_kind="invalid_kind")


def test_perception_frame_valid_and_invalid():
    pf = PerceptionFrame(source_id="cam", frame_index=1, timestamp_ns=1000)
    assert pf.hands == ()

    with pytest.raises(ValidationError):
        PerceptionFrame(source_id="", frame_index=0, timestamp_ns=0)
    with pytest.raises(ValidationError):
        PerceptionFrame(source_id="cam", frame_index=-1, timestamp_ns=0)
    with pytest.raises(ValidationError):
        PerceptionFrame(source_id="cam", frame_index=0, timestamp_ns=-1)


def test_recognition_hypothesis_semantics():
    hyp = RecognitionHypothesis(
        sign_id="HELLO",
        score=0.85,
        semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
    )
    assert hyp.sign_id == "HELLO"
    assert hyp.score == 0.85

    # Probability out of bounds
    with pytest.raises(ValidationError, match="Probability score"):
        RecognitionHypothesis(
            sign_id="HELLO",
            score=1.5,
            semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
        )

    # Empty sign_id
    with pytest.raises(ValidationError, match="Sign ID"):
        RecognitionHypothesis(
            sign_id="",
            score=0.5,
            semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
        )

    # Non-finite score
    with pytest.raises(ValidationError, match="finite"):
        RecognitionHypothesis(
            sign_id="HELLO",
            score=float("nan"),
            semantics=ScoreSemantics.UNCALIBRATED_SCORE,
        )

    # Distance score can be > 1.0 as long as finite
    dist_hyp = RecognitionHypothesis(
        sign_id="DISTANCE_SIGN",
        score=15.2,
        semantics=ScoreSemantics.DISTANCE,
    )
    assert dist_hyp.score == 15.2


def test_sign_event_single_hand():
    event = SignEvent(
        event_id="ev_001",
        profile_id="test_lang",
        sign_id="SIGN_01",
        start_ns=1000,
        end_ns=2000,
        handedness=(Handedness.RIGHT,),
        hand_tracking_ids=(1,),
        score=0.92,
        score_semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
    )
    assert event.event_id == "ev_001"
    assert event.handedness == (Handedness.RIGHT,)
    assert event.score == 0.92


def test_sign_event_bimanual():
    event = SignEvent(
        event_id="bimanual_001",
        profile_id="test_sign_language",
        sign_id="SIGN_BIMANUAL_01",
        start_ns=100,
        end_ns=500,
        handedness=(Handedness.LEFT, Handedness.RIGHT),
        hand_tracking_ids=(1, 2),
    )
    assert len(event.handedness) == 2
    assert len(event.hand_tracking_ids) == 2


def test_sign_event_validation_errors():
    # Empty ID
    with pytest.raises(ValidationError, match="event ID"):
        SignEvent(event_id="", profile_id="p", sign_id="s", start_ns=0, end_ns=100)
    with pytest.raises(ValidationError, match="profile ID"):
        SignEvent(event_id="e", profile_id="", sign_id="s", start_ns=0, end_ns=100)
    with pytest.raises(ValidationError, match="sign ID"):
        SignEvent(event_id="e", profile_id="p", sign_id="", start_ns=0, end_ns=100)
    # Regressive timestamps
    with pytest.raises(ValidationError, match="timestamps"):
        SignEvent(event_id="e", profile_id="p", sign_id="s", start_ns=200, end_ns=100)
    with pytest.raises(ValidationError, match="timestamps"):
        SignEvent(event_id="e", profile_id="p", sign_id="s", start_ns=-1, end_ns=100)
    # Score without semantics
    with pytest.raises(ValidationError, match="explicit semantics"):
        SignEvent(
            event_id="e",
            profile_id="p",
            sign_id="s",
            start_ns=0,
            end_ns=100,
            score=0.8,
            score_semantics=None,
        )
    # Semantics without score
    with pytest.raises(ValidationError, match="actual score"):
        SignEvent(
            event_id="e",
            profile_id="p",
            sign_id="s",
            start_ns=0,
            end_ns=100,
            score=None,
            score_semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
        )
    # Non-finite score
    with pytest.raises(ValidationError, match="finite"):
        SignEvent(
            event_id="e",
            profile_id="p",
            sign_id="s",
            start_ns=0,
            end_ns=100,
            score=float("nan"),
            score_semantics=ScoreSemantics.UNCALIBRATED_SCORE,
        )
    # Calibrated score out of range
    with pytest.raises(ValidationError, match="between 0.0 and 1.0"):
        SignEvent(
            event_id="e",
            profile_id="p",
            sign_id="s",
            start_ns=0,
            end_ns=100,
            score=1.5,
            score_semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
        )


def test_translation_output_validation():
    out = TranslationOutput(
        locale="es-CO",
        text="Hola mundo",
        profile_id="lsc",
        event_ids=("ev1",),
    )
    assert out.locale == "es-CO"
    assert out.text == "Hola mundo"

    with pytest.raises(ValidationError, match="locale"):
        TranslationOutput(locale="", text="Hello", profile_id="lsc")
    with pytest.raises(ValidationError, match="text"):
        TranslationOutput(locale="en-US", text="  ", profile_id="lsc")
    with pytest.raises(ValidationError, match="profile ID"):
        TranslationOutput(locale="en-US", text="Hello", profile_id="")


def test_language_profile_validation():
    prof = LanguageProfile(
        profile_id="lsc",
        display_name="Lengua de Señas Colombiana",
        source_language_code=None,
        vocabulary_version="1.0",
        output_locales=("es-CO", "en-US"),
        capabilities=frozenset({"static_signs"}),
    )
    assert prof.profile_id == "lsc"

    with pytest.raises(ValidationError, match="profile ID"):
        LanguageProfile(
            profile_id="",
            display_name="D",
            source_language_code=None,
            vocabulary_version="1.0",
            output_locales=("es-CO",),
            capabilities=frozenset(),
        )
    with pytest.raises(ValidationError, match="display name"):
        LanguageProfile(
            profile_id="lsc",
            display_name="",
            source_language_code=None,
            vocabulary_version="1.0",
            output_locales=("es-CO",),
            capabilities=frozenset(),
        )
    with pytest.raises(ValidationError, match="vocabulary version"):
        LanguageProfile(
            profile_id="lsc",
            display_name="D",
            source_language_code=None,
            vocabulary_version="",
            output_locales=("es-CO",),
            capabilities=frozenset(),
        )
    with pytest.raises(ValidationError, match="locale identifier"):
        LanguageProfile(
            profile_id="lsc",
            display_name="D",
            source_language_code=None,
            vocabulary_version="1.0",
            output_locales=("INVALID LOCALE!!",),
            capabilities=frozenset(),
        )
    with pytest.raises(ValidationError, match="Duplicate output locales"):
        LanguageProfile(
            profile_id="lsc",
            display_name="D",
            source_language_code=None,
            vocabulary_version="1.0",
            output_locales=("es-CO", "es-CO"),
            capabilities=frozenset(),
        )
