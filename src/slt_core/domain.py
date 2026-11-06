"""SLT Core Domain Model and Typed Data Contracts."""
from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from math import isfinite

from slt_core.errors import ValidationError


class Handedness(StrEnum):
    LEFT = "left"
    RIGHT = "right"
    UNKNOWN = "unknown"


class ScoreSemantics(StrEnum):
    CALIBRATED_PROBABILITY = "calibrated_probability"
    UNCALIBRATED_SCORE = "uncalibrated_score"
    DISTANCE = "distance"


@dataclass(frozen=True, slots=True)
class Landmark:
    """Single 3D coordinate point."""
    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for value in (self.x, self.y, self.z):
            if not isfinite(value):
                raise ValidationError("Landmark coordinates must be finite.")


@dataclass(frozen=True, slots=True)
class HandObservation:
    """Anatomical observation of a single hand."""
    tracking_id: int
    handedness: Handedness
    landmarks: tuple[Landmark, ...]
    world_landmarks: tuple[Landmark, ...] = ()
    detection_score: float | None = None

    def __post_init__(self) -> None:
        if self.tracking_id < 0:
            raise ValidationError("Tracking ID must be non-negative.")
        if len(self.landmarks) != 21:
            raise ValidationError(f"Hand must have 21 landmarks, got {len(self.landmarks)}.")
        if self.world_landmarks and len(self.world_landmarks) != 21:
            raise ValidationError(f"World landmarks must have 21 points, got {len(self.world_landmarks)}.")
        if self.detection_score is not None and (
            not isfinite(self.detection_score) or not (0.0 <= self.detection_score <= 1.0)
        ):
            raise ValidationError("Detection score must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class FramePacket:
    """Atomic input frame from any camera or video source."""
    source_id: str
    frame_index: int
    timestamp_ns: int
    image: bytes | object | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValidationError("Source ID cannot be empty.")
        if self.frame_index < 0:
            raise ValidationError("Frame index must be non-negative.")
        if self.timestamp_ns < 0:
            raise ValidationError("Timestamp must be non-negative.")


@dataclass(frozen=True, slots=True)
class PerceptionFrame:
    """Anatomical perception result for a frame packet."""
    source_id: str
    frame_index: int
    timestamp_ns: int
    hands: tuple[HandObservation, ...] = ()

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValidationError("Source ID cannot be empty.")
        if self.frame_index < 0:
            raise ValidationError("Frame index must be non-negative.")
        if self.timestamp_ns < 0:
            raise ValidationError("Timestamp must be non-negative.")


@dataclass(frozen=True, slots=True)
class RecognitionHypothesis:
    """Candidate sign recognition score from the classifier."""
    sign_id: str
    score: float
    semantics: ScoreSemantics

    def __post_init__(self) -> None:
        if not self.sign_id.strip():
            raise ValidationError("Sign ID cannot be empty.")
        if not isfinite(self.score):
            raise ValidationError("Hypothesis score must be finite.")
        if (
            self.semantics == ScoreSemantics.CALIBRATED_PROBABILITY
            and not (0.0 <= self.score <= 1.0)
        ):
            raise ValidationError("Probability score must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class SignEvent:
    """
    Confirmed linguistic sign event emitted by the temporal decoder.
    Supports single hand and bimanual signs.
    """
    event_id: str
    profile_id: str
    sign_id: str
    start_ns: int
    end_ns: int
    handedness: tuple[Handedness, ...] = ()
    hand_tracking_ids: tuple[int, ...] = ()
    score: float | None = None
    score_semantics: ScoreSemantics | None = None

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValidationError("Invalid event ID.")
        if not self.profile_id.strip():
            raise ValidationError("Invalid profile ID.")
        if not self.sign_id.strip():
            raise ValidationError("Invalid sign ID.")
        if self.start_ns < 0 or self.end_ns < self.start_ns:
            raise ValidationError("Invalid event timestamps.")
        if self.score is None and self.score_semantics is not None:
            raise ValidationError("Score semantics require an actual score.")
        if self.score is not None and self.score_semantics is None:
            raise ValidationError("A score requires explicit semantics.")
        if self.score is not None and not isfinite(self.score):
            raise ValidationError("Score must be finite.")
        if (
            self.score is not None
            and self.score_semantics == ScoreSemantics.CALIBRATED_PROBABILITY
            and not (0.0 <= self.score <= 1.0)
        ):
            raise ValidationError("Calibrated probability must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class TranslationOutput:
    """Realized translation in a specific target locale."""
    locale: str
    text: str
    profile_id: str
    event_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.locale.strip():
            raise ValidationError("Invalid locale.")
        if not self.text.strip():
            raise ValidationError("Invalid translation text.")
        if not self.profile_id.strip():
            raise ValidationError("Invalid profile ID.")


@dataclass(frozen=True, slots=True)
class LanguageProfile:
    """Sovereign sign language profile configuration."""
    profile_id: str
    display_name: str
    source_language_code: str | None
    vocabulary_version: str
    output_locales: tuple[str, ...]
    capabilities: frozenset[str]

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValidationError("Invalid profile ID.")
        if not self.display_name.strip():
            raise ValidationError("Invalid display name.")
        if not self.vocabulary_version.strip():
            raise ValidationError("Invalid vocabulary version.")
        if len(self.output_locales) != len(set(self.output_locales)):
            raise ValidationError("Duplicate output locales.")
        locale_pattern = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
        for locale in self.output_locales:
            if not locale_pattern.fullmatch(locale):
                raise ValidationError(f"Invalid locale identifier: {locale}")


@dataclass(frozen=True, slots=True)
class PipelineFrameResult:
    """Consolidated execution result for a single frame packet."""
    source_id: str
    frame_index: int
    timestamp_ns: int
    perception: PerceptionFrame
    hypotheses: tuple[RecognitionHypothesis, ...]
    new_events: tuple[SignEvent, ...]
    translations: tuple[TranslationOutput, ...]
    processing_time_ns: int
