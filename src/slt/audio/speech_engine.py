"""Asynchronous speech engine using Windows SAPI5 with pyttsx3 fallback."""
from __future__ import annotations
import sys
import queue
import threading

class SpeechEngine:
    """
    Robust asynchronous speech synthesis engine.
    Uses native SAPI5 on Windows with thread-safe COM initialization to prevent
    the known event-loop freezing bug of pyttsx3.
    """
    def __init__(self, rate: int = 0):
        self.rate = rate
        self.queue: queue.Queue[tuple[str, str] | None] = queue.Queue()
        self.stop_event = threading.Event()
        self.ready_event = threading.Event()
        self.voices: dict[str, tuple[object, str]] = {}
        self.backend = "none"

        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.thread.start()
        self.ready_event.wait(timeout=5.0)

    def speak(self, text: str, language: str = "es"):
        """Enqueue text for pronunciation. Language can be 'es' or 'en'."""
        if not text or not text.strip():
            return
        self.queue.put((text.strip(), language.lower()))

    def speak_bilingual(self, text_es: str, text_en: str, mode: str = "both"):
        """
        Pronounce based on selected mode:
          - 'es': Spanish phrase only
          - 'en': English phrase only
          - 'both': Spanish followed by English
        """
        if mode == "es":
            self.speak(text_es, "es")
        elif mode == "en":
            self.speak(text_en, "en")
        elif mode == "both":
            if text_es:
                self.speak(text_es, "es")
            if text_en:
                self.speak(text_en, "en")

    def wait_until_done(self):
        """Wait for queue to finish."""
        self.queue.join()

    def stop(self):
        self.stop_event.set()
        self.queue.put(None)

    def _worker(self):
        speak_fn = None
        if sys.platform == "win32":
            try:
                speak_fn = self._setup_sapi()
            except Exception as e:
                print(f"[SpeechEngine] SAPI5 inicialización falló ({e}), probando fallback.")

        if speak_fn is None:
            try:
                speak_fn = self._setup_pyttsx3()
            except Exception as e:
                print(f"[SpeechEngine] pyttsx3 fallback falló ({e}). Modo silencioso activo.")

        self.ready_event.set()

        while not self.stop_event.is_set():
            try:
                item = self.queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                self.queue.task_done()
                break

            text, lang = item
            try:
                if speak_fn:
                    speak_fn(text, lang)
                else:
                    print(f"[TTS {lang.upper()}]: {text}")
            except Exception as ex:
                print(f"[SpeechEngine Error]: {ex}")
            finally:
                self.queue.task_done()

    def _setup_sapi(self):
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()

        voice_obj = comtypes.client.CreateObject("SAPI.SpVoice")
        tokens = voice_obj.GetVoices()

        for i in range(tokens.Count):
            token = tokens.Item(i)
            desc = token.GetDescription()
            try:
                lang_attr = token.GetAttribute("Language").split(";")[0]
                primary_lang_id = int(lang_attr, 16) & 0x3FF
                detected_lang = {0x0A: "es", 0x09: "en"}.get(primary_lang_id)
            except Exception:
                desc_lower = desc.lower()
                if any(k in desc_lower for k in ("spanish", "español", "helena", "sabina", "laura")):
                    detected_lang = "es"
                elif any(k in desc_lower for k in ("english", "zira", "david", "mark")):
                    detected_lang = "en"
                else:
                    detected_lang = None

            if detected_lang and detected_lang not in self.voices:
                self.voices[detected_lang] = (token, desc)

        voice_obj.Rate = int(self.rate)
        self.backend = "SAPI5"

        def speak(text: str, lang: str):
            if lang in self.voices:
                voice_obj.Voice = self.voices[lang][0]
            voice_obj.Speak(text, 0)  # Synchronous within this background thread

        return speak

    def _setup_pyttsx3(self):
        import pyttsx3
        engine = pyttsx3.init()
        for v in engine.getProperty("voices"):
            desc = f"{v.name} {v.id}".lower()
            if "es" not in self.voices and any(k in desc for k in ("spanish", "español", "helena")):
                self.voices["es"] = (v.id, v.name)
            elif "en" not in self.voices and any(k in desc for k in ("english", "zira", "david")):
                self.voices["en"] = (v.id, v.name)
        engine.stop()
        self.backend = "pyttsx3"

        def speak(text: str, lang: str):
            # Recreate engine per call on secondary thread to avoid Windows COM lockup
            e = pyttsx3.init()
            e.setProperty("rate", 160 + self.rate * 15)
            if lang in self.voices:
                e.setProperty("voice", self.voices[lang][0])
            e.say(text)
            e.runAndWait()
            e.stop()

        return speak
