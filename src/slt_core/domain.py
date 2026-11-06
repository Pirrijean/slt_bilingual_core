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
    # ID asignado por SLT HandTracker.
    tracking_id: int | None
    handedness: Handedness
    # Coordenadas normalizadas de imagen.
    landmarks: tuple[Landmark, ...]
    # Coordenadas tridimensionales de mundo.
    world_landmarks: tuple[Landmark, ...]
    # Score de la clasificación Left/Right.
    # NO es una confianza general de todos los landmarks.
    handedness_score: float | None = None

    def __post_init__(self) -> None:
        if len(self.landmarks) != 21:
            raise ValidationError("A hand must contain 21 image landmarks.")
        if len(self.world_landmarks) != 21:
            raise ValidationError("A hand must contain 21 world landmarks.")
        if self.tracking_id is not None and self.tracking_id < 0:
            raise ValidationError("tracking_id cannot be negative.")
        if self.handedness_score is not None and (
            not isfinite(self.handedness_score) or not (0.0 <= self.handedness_score <= 1.0)
        ):
            raise ValidationError("handedness_score must be between 0.0 and 1.0.")


@dataclass(frozen=True, slots=True)
class FramePacket:
    """Atomic input frame from any camera or video source."""
    source_id: str
    frame_index: int
    timestamp_ns: int
    # Imagen BGR uint8 en formato H x W x 3.
    image: object = None
    pixel_format: str = "BGR24"
    # monotonic: cámara en vivo.
    # presentation: tiempo del vídeo obtenido mediante PTS.
    timestamp_kind: str = "monotonic"
    # Información de origen del vídeo.
    # Se conserva para auditoría y sincronización.
    presentation_pts: int | None = None
    time_base_num: int | None = None
    time_base_den: int | None = None
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source_id.strip():
            raise ValidationError("source_id cannot be empty.")
        if self.frame_index < 0:
            raise ValidationError("frame_index cannot be negative.")
        if self.timestamp_ns < 0:
            raise ValidationError("timestamp_ns cannot be negative.")
        if self.timestamp_kind not in ("monotonic", "presentation"):
            raise ValidationError(f"Invalid timestamp_kind: {self.timestamp_kind}")


@dataclass(frozen=True, slots=True)
class FaceObservation:
    """Anatomical observation of a detected face."""
    tracking_id: int | None
    landmarks: tuple[Landmark, ...]
    blendshapes: tuple[tuple[str, float], ...] = ()
    transformation_matrix: tuple[float, ...] | None = None

    def __post_init__(self) -> None:
        if self.tracking_id is not None and self.tracking_id < 0:
            raise ValidationError("tracking_id cannot be negative.")


@dataclass(frozen=True, slots=True)
class PoseLandmark:
    """3D Pose landmark with optional visibility and presence scores."""
    x: float
    y: float
    z: float
    visibility: float | None = None
    presence: float | None = None

    def __post_init__(self) -> None:
        for val in (self.x, self.y, self.z):
            if not isfinite(val):
                raise ValidationError("PoseLandmark coordinates must be finite.")
        if self.visibility is not None and not isfinite(self.visibility):
            raise ValidationError("PoseLandmark visibility must be finite.")
        if self.presence is not None and not isfinite(self.presence):
            raise ValidationError("PoseLandmark presence must be finite.")


@dataclass(frozen=True, slots=True)
class PoseObservation:
    """Anatomical observation of a detected human pose (body skeleton)."""
    tracking_id: int | None
    landmarks: tuple[PoseLandmark, ...]
    world_landmarks: tuple[PoseLandmark, ...] = ()

    def __post_init__(self) -> None:
        if self.tracking_id is not None and self.tracking_id < 0:
            raise ValidationError("tracking_id cannot be negative.")


@dataclass(frozen=True, slots=True)
class PerceptionFrame:
    """Anatomical perception result for a frame packet across all modalities."""
    source_id: str
    frame_index: int
    timestamp_ns: int
    hands: tuple[HandObservation, ...] = ()
    faces: tuple[FaceObservation, ...] = ()
    poses: tuple[PoseObservation, ...] = ()

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
