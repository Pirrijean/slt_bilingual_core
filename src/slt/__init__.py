"""
SLT Bilingual Core: Modular Bilingual Sign Language Recognition & Translation.
"""
__version__ = "1.0.0"
__author__ = "Pirrijean <jp.ninor1@uniandes.edu.co>"

from slt.capture import CameraWorker
from slt.perception import HandDetector, draw_hand_skeleton, PerceptionResult, DetectedHand
from slt.recognition import extract_features, SLTClassifier, SignRecognizer
from slt.interaction import SLTInteractionEngine, SignEvent, InteractionState
from slt.language import BilingualTranslator, SemanticFrame, Lexicon
from slt.speech import SpeechEngine, SpeechWorker

__all__ = [
    "CameraWorker",
    "HandDetector",
    "draw_hand_skeleton",
    "PerceptionResult",
    "DetectedHand",
    "extract_features",
    "SLTClassifier",
    "SignRecognizer",
    "SLTInteractionEngine",
    "SignEvent",
    "InteractionState",
    "BilingualTranslator",
    "SemanticFrame",
    "Lexicon",
    "SpeechEngine",
    "SpeechWorker",
]
