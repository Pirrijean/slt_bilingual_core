"""SLT Core Pipeline."""
from __future__ import annotations

from collections.abc import Sequence
from time import perf_counter_ns

from slt_core.contracts import (
    PerceptionBackend,
    RecognitionBackend,
    TemporalDecoder,
    TranslationBackend,
)
from slt_core.domain import (
    FramePacket,
    LanguageProfile,
    PerceptionFrame,
    PipelineFrameResult,
    SignEvent,
    TranslationOutput,
)
from slt_core.errors import (
    ClosedPipelineError,
    ComponentContractError,
    ComponentNotReadyError,
    TimestampOrderError,
    ValidationError,
)
from slt_core.phrase_buffer import PhraseBuffer


class CorePipeline:
    """
    Decoupled processing pipeline connecting perception, sign recognition,
    temporal decoding, phrase buffering, and multi-locale translation.
    """

    def __init__(
        self,
        perception: PerceptionBackend,
        recognizer: RecognitionBackend,
        temporal_decoder: TemporalDecoder,
        translator: TranslationBackend,
        profile: LanguageProfile,
        target_locales: Sequence[str] | None = None,
    ) -> None:
        self.perception = perception
        self.recognizer = recognizer
        self.temporal_decoder = temporal_decoder
        self.translator = translator
        self.profile = profile

        if target_locales is None:
            self.target_locales: tuple[str, ...] = tuple(profile.output_locales)
        else:
            locales_tuple = tuple(target_locales)
            for loc in locales_tuple:
                if loc not in profile.output_locales:
                    raise ValidationError(
                        f"Requested locale '{loc}' is not supported by profile '{profile.profile_id}'."
                    )
            self.target_locales = locales_tuple

        self.phrase_buffer = PhraseBuffer()
        self._last_frame_index_by_source: dict[str, int] = {}
        self._last_timestamp_by_source: dict[str, int] = {}
        self._bound_source_id: str | None = None
        self._is_closed: bool = False

    @property
    def is_closed(self) -> bool:
        """True if the pipeline has been closed."""
        return self._is_closed

    def process_frame(self, packet: FramePacket) -> PipelineFrameResult:
        """
        Process a single video or camera frame through perception, recognition,
        temporal decoding, and translation.
        """
        if self._is_closed:
            raise ClosedPipelineError("Pipeline is closed.")

        if self._bound_source_id is None:
            self._bound_source_id = packet.source_id
        elif packet.source_id != self._bound_source_id:
            raise ComponentContractError("One CorePipeline instance must process one source.")

        if not self.perception.ready:
            raise ComponentNotReadyError("Perception backend is not ready.")
        if not self.recognizer.ready:
            raise ComponentNotReadyError("Recognizer backend is not ready.")
        if not self.temporal_decoder.ready:
            raise ComponentNotReadyError("Temporal decoder is not ready.")
        if not self.translator.ready:
            raise ComponentNotReadyError("Translator backend is not ready.")

        # Validate sequence monotonicity per source
        previous_index = self._last_frame_index_by_source.get(packet.source_id)
        if previous_index is not None and packet.frame_index <= previous_index:
            raise TimestampOrderError(
                f"Frame indexes must increase for each source. "
                f"Source '{packet.source_id}': previous {previous_index}, current {packet.frame_index}."
            )
        self._last_frame_index_by_source[packet.source_id] = packet.frame_index

        previous_ts = self._last_timestamp_by_source.get(packet.source_id)
        if previous_ts is not None and packet.timestamp_ns <= previous_ts:
            raise TimestampOrderError(
                f"Timestamps must increase for each source. "
                f"Source '{packet.source_id}': previous {previous_ts}, current {packet.timestamp_ns}."
            )
        self._last_timestamp_by_source[packet.source_id] = packet.timestamp_ns

        start_time_ns = perf_counter_ns()

        # Step 1: Perception
        perception_frame = self.perception.detect(packet)
        if not isinstance(perception_frame, PerceptionFrame):
            raise ComponentContractError("Perception backend did not return a valid PerceptionFrame.")

        # Step 2: Recognition
        hypotheses = tuple(self.recognizer.predict(perception_frame, self.profile))

        # Step 3: Temporal decoding
        new_events = tuple(
            self.temporal_decoder.update(packet.timestamp_ns, hypotheses, perception_frame)
        )

        for event in new_events:
            if event.profile_id != self.profile.profile_id:
                raise ComponentContractError(
                    f"Decoder emitted event for profile '{event.profile_id}', expected '{self.profile.profile_id}'."
                )
            if event.end_ns > packet.timestamp_ns:
                raise ComponentContractError(
                    f"Decoder emitted an event beyond the current frame: end_ns {event.end_ns} > timestamp {packet.timestamp_ns}."
                )

        # Step 4: Phrase buffer update
        added_events: list[SignEvent] = []
        for event in new_events:
            if self.phrase_buffer.append(event):
                added_events.append(event)

        # Step 5: Translation
        if added_events:
            raw_translations = self.translator.translate(
                self.phrase_buffer.events, self.profile, self.target_locales
            )
            translations = self._validate_translations(raw_translations)
        else:
            translations = ()

        elapsed_ns = perf_counter_ns() - start_time_ns

        return PipelineFrameResult(
            source_id=packet.source_id,
            frame_index=packet.frame_index,
            timestamp_ns=packet.timestamp_ns,
            perception=perception_frame,
            hypotheses=hypotheses,
            new_events=new_events,
            translations=translations,
            processing_time_ns=elapsed_ns,
        )

    def flush(self) -> tuple[TranslationOutput, ...]:
        """
        Flush any remaining pending events from the temporal decoder and update translations.
        """
        if self._is_closed:
            raise ClosedPipelineError("Pipeline is closed.")
        if not self.temporal_decoder.ready:
            raise ComponentNotReadyError("Temporal decoder is not ready.")
        if not self.translator.ready:
            raise ComponentNotReadyError("Translator backend is not ready.")

        flushed_events = tuple(self.temporal_decoder.flush())
        added = False
        for event in flushed_events:
            if event.profile_id != self.profile.profile_id:
                raise ComponentContractError("Decoder emitted event for another profile during flush.")
            if self.phrase_buffer.append(event):
                added = True

        if added or self.phrase_buffer.events:
            raw_translations = self.translator.translate(
                self.phrase_buffer.events, self.profile, self.target_locales
            )
            return self._validate_translations(raw_translations)

        return ()

    def clear_phrase(self) -> None:
        """Clear the current phrase buffer and reset temporal components."""
        self.phrase_buffer.clear()
        self.temporal_decoder.reset()
        self.translator.reset()

    def close(self) -> None:
        """Close and release all underlying resources safely and idempotently."""
        self._is_closed = True
        errors: list[Exception] = []

        for comp, action in (
            (self.perception, "close"),
            (self.recognizer, "close"),
            (self.temporal_decoder, "close" if hasattr(self.temporal_decoder, "close") else "reset"),
            (self.translator, "close" if hasattr(self.translator, "close") else "reset"),
        ):
            try:
                getattr(comp, action)()
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        if errors:
            raise ComponentContractError(f"Error(s) occurred while closing pipeline: {errors}")

    def _validate_translations(
        self, outputs: Sequence[TranslationOutput]
    ) -> tuple[TranslationOutput, ...]:
        """Validate that translation output conforms strictly to contract and requested locales."""
        outputs_tuple = tuple(outputs)
        locales = [output.locale for output in outputs_tuple]

        if len(locales) != len(set(locales)):
            raise ComponentContractError("Duplicate translation locales.")

        if set(locales) != set(self.target_locales):
            raise ComponentContractError(
                "The translation engine must return all requested output locales."
            )

        known_event_ids = {event.event_id for event in self.phrase_buffer.events}
        for output in outputs_tuple:
            if output.profile_id != self.profile.profile_id:
                raise ComponentContractError(
                    f"Translation profile mismatch: '{output.profile_id}' != '{self.profile.profile_id}'."
                )
            if not set(output.event_ids).issubset(known_event_ids):
                raise ComponentContractError(
                    "Translation references unknown or future event IDs."
                )

        return outputs_tuple
