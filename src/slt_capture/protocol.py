"""LSC data capture protocol loader and validator."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class ProtocolError(ValueError):
    """Raised when a capture protocol fails schema or consistency validation."""


@dataclass(frozen=True, slots=True)
class ProtocolTask:
    """Individual elicitation task within a capture protocol."""

    task_id: str
    task_type: str
    prompt_reference: str
    repetitions: int
    lexical_id: str | None = None
    target_handshape: str | None = None
    linguistic_review_status: str = "pending"


@dataclass(frozen=True, slots=True)
class CaptureProtocol:
    """Formal protocol guiding controlled or continuous sign acquisition."""

    protocol_id: str
    profile_id: str
    mode: str  # "controlled" or "continuous"
    status: str
    title: str
    resolution: tuple[int, int]
    minimum_fps: int
    audio_enabled: bool
    preserve_original: bool
    tasks: tuple[ProtocolTask, ...] = field(default_factory=tuple)


def load_protocol_from_file(protocol_path: str | Path) -> CaptureProtocol:
    """Load and validate a capture protocol JSON file."""
    path = Path(protocol_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Protocol file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Malformed protocol JSON {path.name}: {exc}") from exc

    protocol_id = data.get("protocol_id")
    profile_id = data.get("profile_id")
    mode = data.get("mode")
    title = data.get("title", "")
    status = data.get("status", "draft")

    if not protocol_id or not profile_id or not mode:
        raise ProtocolError("Protocol missing required fields: protocol_id, profile_id, or mode.")

    rec_spec = data.get("recording", {})
    res_list = rec_spec.get("resolution", [1920, 1080])
    resolution = (int(res_list[0]), int(res_list[1]))
    minimum_fps = int(rec_spec.get("minimum_fps", 30))
    audio_enabled = bool(rec_spec.get("audio_enabled", False))
    preserve_original = bool(rec_spec.get("preserve_original", True))

    task_list = []
    for t_data in data.get("tasks", []):
        task_list.append(
            ProtocolTask(
                task_id=t_data["task_id"],
                task_type=t_data["task_type"],
                prompt_reference=t_data["prompt_reference"],
                repetitions=int(t_data.get("repetitions", 1)),
                lexical_id=t_data.get("lexical_id"),
                target_handshape=t_data.get("target_handshape"),
                linguistic_review_status=t_data.get("linguistic_review_status", "pending"),
            )
        )

    return CaptureProtocol(
        protocol_id=protocol_id,
        profile_id=profile_id,
        mode=mode,
        status=status,
        title=title,
        resolution=resolution,
        minimum_fps=minimum_fps,
        audio_enabled=audio_enabled,
        preserve_original=preserve_original,
        tasks=tuple(task_list),
    )
