"""SLT Bilingual Core."""
__version__ = "0.1.0"

from slt_core.domain import (
    FramePacket,
    Handedness,
    HandObservation,
    Landmark,
    LanguageProfile,
    PerceptionFrame,
    PipelineFrameResult,
    RecognitionHypothesis,
    ScoreSemantics,
    SignEvent,
    TranslationOutput,
)
from slt_core.pipeline import CorePipeline

__all__ = [
    "CorePipeline",
    "FramePacket",
    "HandObservation",
    "Handedness",
    "Landmark",
    "LanguageProfile",
    "PerceptionFrame",
    "PipelineFrameResult",
    "RecognitionHypothesis",
    "ScoreSemantics",
    "SignEvent",
    "TranslationOutput",
    "__version__",
]
