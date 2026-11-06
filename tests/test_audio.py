"""Integration tests for asynchronous speech synthesis."""
import time

from slt.speech import SpeechEngine


def test_speech_engine_lifecycle():
    engine = SpeechEngine(mode="both")
    engine.speak("Prueba de audio", "Audio test")
    time.sleep(0.5)
    engine.stop()

def test_speech_multiple_consecutive():
    engine = SpeechEngine(mode="both")
    engine.speak("Hola", "Hello")
    engine.speak("Gracias", "Thank you")
    time.sleep(0.5)
    engine.stop()
