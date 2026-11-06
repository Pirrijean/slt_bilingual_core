"""Integration tests for SAPI5 asynchronous speech engine."""
import time
from slt.audio.speech_engine import SpeechEngine

def test_speech_engine_lifecycle():
    engine = SpeechEngine(rate=2)
    assert engine.ready_event.is_set()

    # Test pronunciation queue
    engine.speak("Prueba de audio en español", "es")
    engine.speak("Audio test in English", "en")
    engine.wait_until_done()

    engine.stop()
    assert engine.stop_event.is_set()

def test_speech_multiple_consecutive():
    engine = SpeechEngine(rate=3)
    phrases = [
        ("Hola", "es"),
        ("Gracias", "es"),
        ("Hello", "en"),
        ("Thank you", "en")
    ]
    for text, lang in phrases:
        engine.speak(text, lang)

    engine.wait_until_done()
    engine.stop()
