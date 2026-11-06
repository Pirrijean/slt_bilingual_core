"""SLT Core Protocol Contracts."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from slt_core.domain import (
    FramePacket,
    LanguageProfile,
    PerceptionFrame,
    RecognitionHypothesis,
    SignEvent,
    TranslationOutput,
)


@runtime_checkable
class PerceptionBackend(Protocol):
    """Anatomical perception: turns raw video frames into anatomical landmarks."""

    @property
    def ready(self) -> bool:
        ...

    def detect(self, packet: FramePacket) -> PerceptionFrame:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class RecognitionBackend(Protocol):
    """Translates anatomical landmarks into sign classification hypotheses."""

    @property
    def ready(self) -> bool:
        ...

    def predict(
        self,
        perception: PerceptionFrame,
        profile: LanguageProfile,
    ) -> tuple[RecognitionHypothesis, ...]:
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class TemporalDecoder(Protocol):
    """Filters noisy hypotheses across time into confirmed sign events."""

    @property
    def ready(self) -> bool:
        ...

    def update(
        self,
        timestamp_ns: int,
        hypotheses: tuple[RecognitionHypothesis, ...],
        perception: PerceptionFrame,
    ) -> tuple[SignEvent, ...]:
        ...

    def flush(self) -> tuple[SignEvent, ...]:
        ...

    def reset(self) -> None:
        ...


@runtime_checkable
class TranslationBackend(Protocol):
    """Realizes sign sequences into target spoken written languages."""

    @property
    def ready(self) -> bool:
        ...

    def translate(
        self,
        events: tuple[SignEvent, ...],
        profile: LanguageProfile,
        target_locales: tuple[str, ...],
    ) -> tuple[TranslationOutput, ...]:
        ...

    def reset(self) -> None:
        ...


@runtime_checkable
class FrameSource(Protocol):
    """Decoupled video/camera frame provider."""

    @property
    def source_id(self) -> str:
        ...

    @property
    def ready(self) -> bool:
        ...

    def read(self) -> FramePacket | None:
        """Return the next frame or None at end-of-stream."""
        ...

    def close(self) -> None:
        ...


@runtime_checkable
class SpeechBackend(Protocol):
    """Decoupled speech synthesis provider."""

    @property
    def ready(self) -> bool:
        ...

    def enqueue(self, text: str, locale: str) -> None:
        """Queue speech without blocking the calling thread."""
        ...

    def close(self) -> None:
        ...
