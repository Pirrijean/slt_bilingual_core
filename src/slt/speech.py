#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Speech Synthesis Module.
Provides non-blocking, multi-threaded text-to-speech with native Spanish and English voices.
Uses direct SAPI5 COM dispatch on Windows to prevent threading deadlocks.
"""
import sys
import threading
import queue
import logging
from typing import Optional
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("slt.speech")

class SpeechEngine:
    """
    Asynchronous Speech Engine maintaining an internal worker thread and message queue.
    Guarantees non-blocking execution so the UI never stutters during speech output.
    """
    def __init__(self, mode: str = "both"):
        self.mode = mode  # "es", "en", "both"
        self._queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._worker_thread.start()

    def set_mode(self, mode: str):
        if mode in ("es", "en", "both"):
            self.mode = mode

    def speak(self, es_text: str, en_text: str):
        """Enqueue texts for asynchronous speech output."""
        if not self._stop_event.is_set():
            self._queue.put((es_text, en_text, self.mode))

    def stop(self):
        """Signal worker thread to terminate and wait."""
        self._stop_event.set()
        self._queue.put(None)
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)

    def _run_loop(self):
        """Worker thread loop initializing COM and servicing speech requests."""
        is_windows = sys.platform == "win32"
        sapi_voice = None
        es_voice_token = None
        en_voice_token = None

        if is_windows:
            try:
                import comtypes
                import comtypes.client
                comtypes.CoInitialize()
                sapi_voice = comtypes.client.CreateObject("SAPI.SpVoice")
                tokens = sapi_voice.GetVoices()
                
                for i in range(tokens.Count):
                    token = tokens.Item(i)
                    desc = token.GetDescription().lower()
                    if "spanish" in desc or "helena" in desc or "sabina" in desc or "raul" in desc:
                        if es_voice_token is None:
                            es_voice_token = token
                    elif "zira" in desc or "david" in desc or "english" in desc:
                        if en_voice_token is None:
                            en_voice_token = token

                logger.info(f"SAPI5 Voice initialized. ES: {es_voice_token is not None}, EN: {en_voice_token is not None}")
            except Exception as e:
                logger.warning(f"Failed to initialize direct SAPI5 COM: {e}. Falling back to pyttsx3.")
                sapi_voice = None

        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            es_text, en_text, mode = item

            try:
                if sapi_voice:
                    if mode in ("es", "both") and es_text.strip():
                        if es_voice_token:
                            sapi_voice.Voice = es_voice_token
                        sapi_voice.Speak(es_text.strip(), 0)  # 0 = synchronous within worker thread
                    
                    if mode in ("en", "both") and en_text.strip():
                        if en_voice_token:
                            sapi_voice.Voice = en_voice_token
                        sapi_voice.Speak(en_text.strip(), 0)
                else:
                    import pyttsx3
                    engine = pyttsx3.init()
                    if mode in ("es", "both") and es_text.strip():
                        engine.say(es_text)
                    if mode in ("en", "both") and en_text.strip():
                        engine.say(en_text)
                    engine.runAndWait()
            except Exception as e:
                logger.error(f"Speech synthesis error: {e}")
            finally:
                self._queue.task_done()

        if is_windows and sapi_voice:
            try:
                import comtypes
                comtypes.CoUninitialize()
            except Exception:
                pass


class SpeechWorker(QObject):
    """PySide6 QObject wrapper for UI signal integration."""
    speech_enqueued = Signal(str, str)

    def __init__(self, mode: str = "both"):
        super().__init__()
        self.engine = SpeechEngine(mode=mode)

    def speak(self, es_text: str, en_text: str):
        self.engine.speak(es_text, en_text)
        self.speech_enqueued.emit(es_text, en_text)

    def set_mode(self, mode: str):
        self.engine.set_mode(mode)

    def stop(self):
        self.engine.stop()
