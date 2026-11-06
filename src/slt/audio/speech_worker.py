"""PySide6 worker / controller adapter for SpeechEngine."""
from __future__ import annotations
from PySide6.QtCore import QObject, Signal, Slot
from .speech_engine import SpeechEngine

class SpeechWorker(QObject):
    speech_started = Signal(str, str)
    speech_finished = Signal()

    def __init__(self, rate: int = 0):
        super().__init__()
        self.engine = SpeechEngine(rate=rate)

    @Slot(str, str)
    def speak(self, text: str, lang: str = "es"):
        self.engine.speak(text, lang)

    @Slot(str, str, str)
    def speak_bilingual(self, text_es: str, text_en: str, mode: str = "both"):
        self.engine.speak_bilingual(text_es, text_en, mode=mode)

    def close(self):
        self.engine.stop()
