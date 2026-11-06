"""Unit tests for CorePipeline with decoupled test doubles."""
import pytest

from slt_core.domain import (
    FramePacket,
    Handedness,
    LanguageProfile,
    PerceptionFrame,
    RecognitionHypothesis,
    ScoreSemantics,
    SignEvent,
    TranslationOutput,
)
from slt_core.errors import (
    ComponentContractError,
    ComponentNotReadyError,
    TimestampOrderError,
)
from slt_core.pipeline import CorePipeline


class FakePerception:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.closed = False

    def detect(self, packet: FramePacket) -> PerceptionFrame:
        return PerceptionFrame(
            source_id=packet.source_id,
            frame_index=packet.frame_index,
            timestamp_ns=packet.timestamp_ns,
            hands=(),
        )

    def close(self) -> None:
        self.closed = True


class FakeRecognizer:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.closed = False
        self.hypotheses_to_return: tuple[RecognitionHypothesis, ...] = ()

    def predict(
        self, perception: PerceptionFrame, profile: LanguageProfile
    ) -> tuple[RecognitionHypothesis, ...]:
        return self.hypotheses_to_return

    def close(self) -> None:
        self.closed = True


class FakeTemporalDecoder:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.events_to_return: list[SignEvent] = []
        self.flush_events_to_return: list[SignEvent] = []
        self.reset_called = False

    def update(
        self,
        timestamp_ns: int,
        hypotheses: tuple[RecognitionHypothesis, ...],
        perception: PerceptionFrame,
    ) -> tuple[SignEvent, ...]:
        events = tuple(self.events_to_return)
        self.events_to_return.clear()
        return events

    def flush(self) -> tuple[SignEvent, ...]:
        events = tuple(self.flush_events_to_return)
        self.flush_events_to_return.clear()
        return events

    def reset(self) -> None:
        self.reset_called = True


class FakeTranslator:
    def __init__(self, ready: bool = True) -> None:
        self.ready = ready
        self.reset_called = False
        self.custom_outputs: list[TranslationOutput] | None = None

    def translate(
        self,
        events: tuple[SignEvent, ...],
        profile: LanguageProfile,
        target_locales: tuple[str, ...],
    ) -> tuple[TranslationOutput, ...]:
        if self.custom_outputs is not None:
            return tuple(self.custom_outputs)
        text = " ".join(e.sign_id for e in events) if events else ""
        event_ids = tuple(e.event_id for e in events)
        return tuple(
            TranslationOutput(
                locale=loc,
                text=text or "empty",
                profile_id=profile.profile_id,
                event_ids=event_ids,
            )
            for loc in target_locales
        )

    def reset(self) -> None:
        self.reset_called = True


def make_packet(
    frame_index: int,
    timestamp_ns: int,
    source_id: str = "cam_0",
) -> FramePacket:
    return FramePacket(
        source_id=source_id,
        frame_index=frame_index,
        timestamp_ns=timestamp_ns,
        image=None,
    )


def test_full_pipeline_flow(test_profile: LanguageProfile):
    perception = FakePerception()
    recognizer = FakeRecognizer()
    decoder = FakeTemporalDecoder()
    translator = FakeTranslator()

    pipeline = CorePipeline(
        perception=perception,
        recognizer=recognizer,
        temporal_decoder=decoder,
        translator=translator,
        profile=test_profile,
        target_locales=("es-CO", "en-US"),
    )

    # Frame 1: No events emitted yet
    packet1 = make_packet(frame_index=0, timestamp_ns=1000)
    res1 = pipeline.process_frame(packet1)
    assert res1.frame_index == 0
    assert res1.timestamp_ns == 1000
    assert res1.new_events == ()
    assert res1.translations == ()
    assert res1.processing_time_ns > 0

    # Frame 2: Decoder emits an event
    decoder.events_to_return = [
        SignEvent(
            event_id="ev_1",
            profile_id=test_profile.profile_id,
            sign_id="HOLA",
            start_ns=1000,
            end_ns=2000,
            handedness=(Handedness.RIGHT,),
            score=0.95,
            score_semantics=ScoreSemantics.CALIBRATED_PROBABILITY,
        )
    ]
    packet2 = make_packet(frame_index=1, timestamp_ns=2000)
    res2 = pipeline.process_frame(packet2)
    assert len(res2.new_events) == 1
    assert len(res2.translations) == 2
    assert {t.locale for t in res2.translations} == {"es-CO", "en-US"}
    assert res2.translations[0].text == "HOLA"
    assert len(pipeline.phrase_buffer) == 1


def test_component_readiness_checks(test_profile: LanguageProfile):
    # Perception not ready
    p = CorePipeline(
        perception=FakePerception(ready=False),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(),
        profile=test_profile,
    )
    with pytest.raises(ComponentNotReadyError, match="Perception backend"):
        p.process_frame(make_packet(0, 1000))

    # Recognizer not ready
    p = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(ready=False),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(),
        profile=test_profile,
    )
    with pytest.raises(ComponentNotReadyError, match="Recognizer backend"):
        p.process_frame(make_packet(0, 1000))

    # Decoder not ready
    p = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(ready=False),
        translator=FakeTranslator(),
        profile=test_profile,
    )
    with pytest.raises(ComponentNotReadyError, match="Temporal decoder"):
        p.process_frame(make_packet(0, 1000))

    # Translator not ready
    p = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(ready=False),
        profile=test_profile,
    )
    with pytest.raises(ComponentNotReadyError, match="Translator backend"):
        p.process_frame(make_packet(0, 1000))


def test_frame_index_and_timestamp_monotonicity(test_profile: LanguageProfile):
    pipeline = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(),
        profile=test_profile,
    )

    pipeline.process_frame(make_packet(frame_index=1, timestamp_ns=1000))

    # Regressive frame index
    with pytest.raises(TimestampOrderError, match="Frame indexes must increase"):
        pipeline.process_frame(make_packet(frame_index=1, timestamp_ns=2000))

    # Regressive timestamp
    with pytest.raises(TimestampOrderError, match="Timestamps must increase"):
        pipeline.process_frame(make_packet(frame_index=2, timestamp_ns=900))


def test_multi_source_isolation(test_profile: LanguageProfile):
    pipeline = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(),
        profile=test_profile,
    )

    # Source A at index 10, ts 10000
    res_a = pipeline.process_frame(make_packet(frame_index=10, timestamp_ns=10000, source_id="cam_A"))
    assert res_a.source_id == "cam_A"

    # Source B at index 1, ts 1000 (earlier than A, but valid for B)
    res_b = pipeline.process_frame(make_packet(frame_index=1, timestamp_ns=1000, source_id="cam_B"))
    assert res_b.source_id == "cam_B"

    # Continuing Source A
    res_a2 = pipeline.process_frame(make_packet(frame_index=11, timestamp_ns=11000, source_id="cam_A"))
    assert res_a2.frame_index == 11


def test_decoder_contract_validation(test_profile: LanguageProfile):
    decoder = FakeTemporalDecoder()
    pipeline = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=decoder,
        translator=FakeTranslator(),
        profile=test_profile,
    )

    # Event for another profile
    decoder.events_to_return = [
        SignEvent(
            event_id="ev_wrong",
            profile_id="other_profile",
            sign_id="HELLO",
            start_ns=500,
            end_ns=1000,
        )
    ]
    with pytest.raises(ComponentContractError, match="Decoder emitted event for profile"):
        pipeline.process_frame(make_packet(0, 1000))

    # Event beyond current frame timestamp
    decoder.events_to_return = [
        SignEvent(
            event_id="ev_future",
            profile_id=test_profile.profile_id,
            sign_id="HELLO",
            start_ns=500,
            end_ns=2000,  # frame timestamp is 1500
        )
    ]
    with pytest.raises(ComponentContractError, match="Decoder emitted an event beyond"):
        pipeline.process_frame(make_packet(1, 1500))


def test_translation_contract_validation(test_profile: LanguageProfile):
    decoder = FakeTemporalDecoder()
    translator = FakeTranslator()
    pipeline = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=decoder,
        translator=translator,
        profile=test_profile,
        target_locales=("es-CO", "en-US"),
    )

    # Helper event to trigger translation with unique event ID each time
    def trigger_event(eid: str):
        decoder.events_to_return = [
            SignEvent(
                event_id=eid,
                profile_id=test_profile.profile_id,
                sign_id="TEST",
                start_ns=500,
                end_ns=1000,
            )
        ]

    # 1. Missing a requested locale
    trigger_event("ev_1")
    translator.custom_outputs = [
        TranslationOutput(locale="es-CO", text="Solo español", profile_id=test_profile.profile_id, event_ids=("ev_1",))
    ]
    with pytest.raises(ComponentContractError, match="return all requested output locales"):
        pipeline.process_frame(make_packet(0, 1000))

    # 2. Duplicate locales
    trigger_event("ev_2")
    translator.custom_outputs = [
        TranslationOutput(locale="es-CO", text="Español 1", profile_id=test_profile.profile_id, event_ids=("ev_2",)),
        TranslationOutput(locale="es-CO", text="Español 2", profile_id=test_profile.profile_id, event_ids=("ev_2",)),
    ]
    with pytest.raises(ComponentContractError, match="Duplicate translation locales"):
        pipeline.process_frame(make_packet(1, 2000))

    # 3. Profile mismatch
    trigger_event("ev_3")
    translator.custom_outputs = [
        TranslationOutput(locale="es-CO", text="Español", profile_id="wrong_profile", event_ids=("ev_3",)),
        TranslationOutput(locale="en-US", text="English", profile_id=test_profile.profile_id, event_ids=("ev_3",)),
    ]
    with pytest.raises(ComponentContractError, match="Translation profile mismatch"):
        pipeline.process_frame(make_packet(2, 3000))

    # 4. Reference unknown/future event ID
    trigger_event("ev_4")
    translator.custom_outputs = [
        TranslationOutput(locale="es-CO", text="Español", profile_id=test_profile.profile_id, event_ids=("unknown_ev_999",)),
        TranslationOutput(locale="en-US", text="English", profile_id=test_profile.profile_id, event_ids=("ev_4",)),
    ]
    with pytest.raises(ComponentContractError, match="unknown or future event IDs"):
        pipeline.process_frame(make_packet(3, 4000))


def test_pipeline_additional_edge_cases(test_profile: LanguageProfile):
    # Unsupported target locale raises ValidationError
    with pytest.raises(Exception, match="not supported by profile"):
        CorePipeline(
            perception=FakePerception(),
            recognizer=FakeRecognizer(),
            temporal_decoder=FakeTemporalDecoder(),
            translator=FakeTranslator(),
            profile=test_profile,
            target_locales=("fr-FR",),
        )

    # Invalid perception result contract
    class BadPerception:
        ready = True
        def detect(self, packet): return "not a PerceptionFrame"
        def close(self): pass

    pipeline_bad_perception = CorePipeline(
        perception=BadPerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(),
        profile=test_profile,
    )
    with pytest.raises(ComponentContractError, match="valid PerceptionFrame"):
        pipeline_bad_perception.process_frame(make_packet(0, 1000))

    # Flush on empty buffer returns ()
    pipeline = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=FakeTranslator(),
        profile=test_profile,
    )
    assert pipeline.flush() == ()

    # Flush when decoder not ready or translator not ready
    decoder_not_ready = FakeTemporalDecoder(ready=False)
    p_dec_unready = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=decoder_not_ready,
        translator=FakeTranslator(),
        profile=test_profile,
    )
    with pytest.raises(ComponentNotReadyError, match="Temporal decoder"):
        p_dec_unready.flush()

    translator_not_ready = FakeTranslator(ready=False)
    p_trans_unready = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=FakeTemporalDecoder(),
        translator=translator_not_ready,
        profile=test_profile,
    )
    with pytest.raises(ComponentNotReadyError, match="Translator backend"):
        p_trans_unready.flush()

    # Flush with event belonging to another profile
    decoder_wrong = FakeTemporalDecoder()
    decoder_wrong.flush_events_to_return = [
        SignEvent(
            event_id="ev_wrong",
            profile_id="alien_profile",
            sign_id="HELLO",
            start_ns=100,
            end_ns=200,
        )
    ]
    p_wrong = CorePipeline(
        perception=FakePerception(),
        recognizer=FakeRecognizer(),
        temporal_decoder=decoder_wrong,
        translator=FakeTranslator(),
        profile=test_profile,
    )
    with pytest.raises(ComponentContractError, match="another profile during flush"):
        p_wrong.flush()


def test_flush_clear_and_close(test_profile: LanguageProfile):
    perception = FakePerception()
    recognizer = FakeRecognizer()
    decoder = FakeTemporalDecoder()
    translator = FakeTranslator()

    pipeline = CorePipeline(
        perception=perception,
        recognizer=recognizer,
        temporal_decoder=decoder,
        translator=translator,
        profile=test_profile,
    )

    # Decoder has pending flushed event
    decoder.flush_events_to_return = [
        SignEvent(
            event_id="flush_ev",
            profile_id=test_profile.profile_id,
            sign_id="FLUSHED",
            start_ns=100,
            end_ns=200,
        )
    ]
    flush_translations = pipeline.flush()
    assert len(flush_translations) == 2
    assert len(pipeline.phrase_buffer) == 1

    # Clear phrase
    pipeline.clear_phrase()
    assert len(pipeline.phrase_buffer) == 0
    assert decoder.reset_called is True
    assert translator.reset_called is True

    # Close pipeline
    pipeline.close()
    assert pipeline.is_closed is True
    assert perception.closed is True
    assert recognizer.closed is True

    with pytest.raises(ComponentNotReadyError, match="Pipeline is closed"):
        pipeline.process_frame(make_packet(0, 1000))
    with pytest.raises(ComponentNotReadyError, match="Pipeline is closed"):
        pipeline.flush()
