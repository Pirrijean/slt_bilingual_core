"""Technical and environmental metadata collection for capture sessions."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from slt_corpus.domain import (
    CorpusValidationError,
    validate_iso8601_utc,
    validate_no_direct_identifiers,
    validate_pseudonym_id,
)


@dataclass(frozen=True, slots=True)
class CameraMetadata:
    """Optical and hardware specifications of the capture sensor."""

    device_id: str
    camera_model: str
    width: int
    height: int
    target_fps: float
    backend: str


@dataclass(frozen=True, slots=True)
class EnvironmentMetadata:
    """Controlled studio environmental specifications."""

    lighting_type: str  # e.g. "three_point_diffuse"
    lighting_lux: int
    background_type: str  # e.g. "matte_grey"
    distance_to_signer_cm: int


@dataclass(frozen=True, slots=True)
class SessionCaptureMetadata:
    """Complete metadata record associated with a single recording capture."""

    session_id: str
    signer_id: str
    protocol_id: str
    task_id: str
    operator_id: str
    recorded_at_utc: str
    camera: CameraMetadata
    environment: EnvironmentMetadata
    extra_properties_json: str = "{}"

    def __post_init__(self) -> None:
        if not self.session_id.strip():
            raise CorpusValidationError("session_id cannot be empty.")
        validate_pseudonym_id(self.signer_id, "signer_id")
        validate_iso8601_utc(self.recorded_at_utc, "recorded_at_utc")
        validate_no_direct_identifiers(self.extra_properties_json)

    def to_json(self) -> str:
        """Serialize complete capture metadata to JSON string."""
        data = {
            "session_id": self.session_id,
            "signer_id": self.signer_id,
            "protocol_id": self.protocol_id,
            "task_id": self.task_id,
            "operator_id": self.operator_id,
            "recorded_at_utc": self.recorded_at_utc,
            "camera": asdict(self.camera),
            "environment": asdict(self.environment),
            "extra": json.loads(self.extra_properties_json) if self.extra_properties_json.strip() else {},
        }
        return json.dumps(data, indent=2)
