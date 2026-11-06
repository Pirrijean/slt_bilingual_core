#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Bilingual Core: Linguistic Engine Module.
Transforms discrete sign sequences into language-independent SemanticFrames
and generates natural, grammatically correct Spanish and English utterances.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from slt.utils.paths import DEFAULT_LEXICON_PATH

logger = logging.getLogger("slt.language")

@dataclass
class SemanticFrame:
    """Language-independent intermediate semantic representation of an utterance."""
    action: Optional[str] = None          # e.g., "WANT", "NEED", "GREET", "STATE_WELL"
    subject: Optional[str] = None         # e.g., "FIRST_PERSON", "SECOND_PERSON"
    object: Optional[str] = None          # e.g., "WATER", "FOOD", "HELP"
    polarity: str = "positive"            # "positive" | "negative"
    intention: str = "statement"          # "statement" | "question" | "exclamation" | "request"
    politeness: Optional[str] = None      # "PLEASE", "THANK_YOU", "BOTH", None
    fingerspelled: Optional[str] = None   # Concatenated letters from dactilology
    raw_glosses: List[str] = field(default_factory=list)

class Lexicon:
    """Versioned lexicon provider loaded from JSON configuration."""
    def __init__(self, filepath: Optional[str] = None):
        self.filepath = str(filepath or DEFAULT_LEXICON_PATH)
        self.words: Dict[str, Dict[str, Any]] = {}
        self.phrases: List[Dict[str, Any]] = []
        self.load()

    def load(self):
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.words = data.get("words", {})
            self.phrases = data.get("phrases", [])
            logger.info(f"Loaded lexicon with {len(self.words)} words and {len(self.phrases)} idiom rules.")
        except Exception as e:
            logger.error(f"Error loading lexicon from {self.filepath}: {e}")
            self.words = {}
            self.phrases = []

    def get_word(self, gloss: str) -> Optional[Dict[str, Any]]:
        return self.words.get(gloss)

    def is_letter(self, gloss: str) -> bool:
        entry = self.words.get(gloss)
        return entry is not None and entry.get("category") == "Vocales"


class BilingualTranslator:
    """
    Bilingual translation engine (ES/EN) driven by semantic frame parsing,
    pro-drop Spanish syntax rules, explicit English pronouns, and dactilology assembly.
    """
    def __init__(self, lexicon: Optional[Lexicon] = None):
        self.lexicon = lexicon or Lexicon()
        self.gloss_buffer: List[str] = []

    def add_gloss(self, gloss: str) -> Tuple[str, str]:
        """Add a recognized gloss and return updated (es, en) translations."""
        if gloss and gloss != "_NADA_":
            self.gloss_buffer.append(gloss)
        return self.translate()

    def remove_last_gloss(self) -> Tuple[str, str]:
        """Remove last gloss and return updated (es, en) translations."""
        if self.gloss_buffer:
            self.gloss_buffer.pop()
        return self.translate()

    def clear(self):
        """Clear the current sentence accumulator."""
        self.gloss_buffer.clear()

    def parse_semantic_frame(self, glosses: List[str]) -> SemanticFrame:
        """Parse raw gloss list into a structured SemanticFrame."""
        frame = SemanticFrame(raw_glosses=list(glosses))
        if not glosses:
            return frame

        # Check for pure dactilology / fingerspelling sequence
        if all(self.lexicon.is_letter(g) for g in glosses):
            frame.fingerspelled = "".join(glosses)
            return frame

        # Check for polite markers
        has_por_favor = "POR_FAVOR" in glosses
        has_gracias = "GRACIAS" in glosses
        if has_por_favor and has_gracias:
            frame.politeness = "BOTH"
        elif has_por_favor:
            frame.politeness = "PLEASE"
        elif has_gracias:
            frame.politeness = "THANK_YOU"

        # Check for polarity
        if "NO" in glosses:
            frame.polarity = "negative"
        elif "SI" in glosses:
            frame.polarity = "positive"

        # Extract semantic roles
        for g in glosses:
            entry = self.lexicon.get_word(g)
            if not entry:
                continue
            role = entry.get("syntactic_role")
            sem_id = entry.get("semantic_id")

            if role == "subject":
                frame.subject = sem_id
            elif role == "verb" or sem_id in ("WANT", "STATE_WELL", "LOVE", "HELP"):
                frame.action = sem_id
            elif role == "object" or sem_id in ("WATER", "FOOD", "HELP"):
                frame.object = sem_id
            elif sem_id == "GREETING":
                frame.action = "GREET"

        # Refine intentions
        if "AYUDA" in glosses:
            frame.intention = "request"
        elif "TU" in glosses and frame.action in ("STATE_WELL", "HELP"):
            frame.intention = "question"

        return frame

    def translate(self, glosses: Optional[List[str]] = None) -> Tuple[str, str]:
        """
        Translate a sequence of glosses to Spanish and English.
        If glosses is None, uses current gloss_buffer.
        """
        seq = self.gloss_buffer if glosses is None else glosses
        if not seq:
            return "", ""

        # Filter out _NADA_
        clean_seq = [g for g in seq if g != "_NADA_"]
        if not clean_seq:
            return "", ""

        # 1. Exact phrase lookup in lexicon
        for p in self.lexicon.phrases:
            if p.get("glosses") == clean_seq:
                return p.get("es", ""), p.get("en", "")

        # 2. Parse into SemanticFrame
        frame = self.parse_semantic_frame(clean_seq)

        # 3. Dactilology spelling output
        if frame.fingerspelled:
            es = f"Palabra: {frame.fingerspelled}."
            en = f"Spelled: {frame.fingerspelled}."
            return es, en

        # 4. Common semantic compositions
        # Emergency help
        if "AYUDA" in clean_seq:
            if "YO" in clean_seq or len(clean_seq) == 1:
                return "¡Necesito ayuda urgente!", "I need urgent help!"
            elif "TU" in clean_seq:
                return "¿Puedes ayudarme, por favor?", "Can you help me, please?"

        # Need / Want Water or Food
        if "QUERER" in clean_seq or "AGUA" in clean_seq or "COMIDA" in clean_seq:
            item_es = "agua" if "AGUA" in clean_seq else ("comida" if "COMIDA" in clean_seq else "")
            item_en = "water" if "AGUA" in clean_seq else ("food" if "COMIDA" in clean_seq else "")
            
            if item_es:
                if "YO" in clean_seq or "QUERER" in clean_seq:
                    es = f"Quiero {item_es}, por favor."
                    en = f"I want {item_en}, please."
                else:
                    es = f"{item_es.capitalize()}, por favor."
                    en = f"{item_en.capitalize()}, please."
                return es, en

        # Greeting combinations
        if "HOLA" in clean_seq:
            if "TU" in clean_seq or "ESTAR_BIEN" in clean_seq:
                return "¡Hola! ¿Cómo estás?", "Hello! How are you?"
            if len(clean_seq) == 1:
                return "¡Hola!", "Hello!"

        # Well-being
        if "ESTAR_BIEN" in clean_seq:
            if "TU" in clean_seq:
                return "¿Estás bien?", "Are you okay?"
            return "Estoy bien, gracias.", "I am doing well, thank you."

        # Affective
        if "TE_QUIERO" in clean_seq:
            return "Te quiero mucho.", "I love you very much."

        # Courtesy & Responses
        if clean_seq == ["SI", "POR_FAVOR"]:
            return "Sí, por favor.", "Yes, please."
        if clean_seq == ["NO", "GRACIAS"]:
            return "No, gracias.", "No, thank you."
        if clean_seq == ["POR_FAVOR", "GRACIAS"]:
            return "Por favor y muchas gracias.", "Please and thank you very much."

        # 5. Fallback grammatical realization word-by-word
        es_parts = []
        en_parts = []
        for g in clean_seq:
            w = self.lexicon.get_word(g)
            if w:
                # Prefer solo string if single token, otherwise translation
                if len(clean_seq) == 1:
                    es_parts.append(w.get("solo_es", w.get("es", g)))
                    en_parts.append(w.get("solo_en", w.get("en", g)))
                else:
                    # Generic dictionary form
                    es_val = w.get("translations", {}).get("es") or (w.get("es") if isinstance(w.get("es"), str) else g)
                    en_val = w.get("translations", {}).get("en") or (w.get("en") if isinstance(w.get("en"), str) else g)
                    es_parts.append(str(es_val))
                    en_parts.append(str(en_val))
            else:
                es_parts.append(g)
                en_parts.append(g)

        es_text = " ".join(es_parts).capitalize()
        en_text = " ".join(en_parts).capitalize()
        if not es_text.endswith((".", "!", "?")):
            es_text += "."
        if not en_text.endswith((".", "!", "?")):
            en_text += "."

        return es_text, en_text


def format_srt_time(seconds: float) -> str:
    """Format float seconds to SRT timecode standard: HH:MM:SS,mmm"""
    sec_int = int(seconds)
    millis = int(round((seconds - sec_int) * 1000))
    if millis >= 1000:
        millis = 999
    hours = sec_int // 3600
    minutes = (sec_int % 3600) // 60
    secs = sec_int % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def generate_srt(
    events: List[Any],
    es_translation: str,
    en_translation: str
) -> Dict[str, str]:
    """
    Generate standard SRT formatted subtitles for video analysis results.
    Returns dictionary with 'bilingual', 'es', and 'en' SRT texts.
    """
    if not events:
        return {"bilingual": "", "es": "", "en": ""}

    t_start_global = min(e.timestamp_start for e in events)
    t_end_global = max(e.timestamp_end for e in events)

    # 1. Bilingual composite SRT
    bilingual_lines = [
        "1",
        f"{format_srt_time(t_start_global)} --> {format_srt_time(t_end_global)}",
        f"ES: {es_translation}",
        f"EN: {en_translation}",
        ""
    ]

    # 2. Spanish only SRT
    es_lines = [
        "1",
        f"{format_srt_time(t_start_global)} --> {format_srt_time(t_end_global)}",
        es_translation,
        ""
    ]

    # 3. English only SRT
    en_lines = [
        "1",
        f"{format_srt_time(t_start_global)} --> {format_srt_time(t_end_global)}",
        en_translation,
        ""
    ]

    # 4. Detailed Gloss Sequence SRT
    gloss_lines = []
    for idx, ev in enumerate(events, start=1):
        gloss_lines.extend([
            str(idx),
            f"{format_srt_time(ev.timestamp_start)} --> {format_srt_time(ev.timestamp_end)}",
            f"[{ev.label}]",
            ""
        ])

    return {
        "bilingual": "\n".join(bilingual_lines),
        "es": "\n".join(es_lines),
        "en": "\n".join(en_lines),
        "glosses": "\n".join(gloss_lines)
    }


def generate_transcription_txt(
    events: List[Any],
    es_translation: str,
    en_translation: str,
    source_name: str = "Video"
) -> str:
    """Generate structured plain text transcription report."""
    lines = [
        "============================================================",
        f"SLT BILINGUAL CORE · REPORTE DE TRADUCCIÓN DE VIDEO",
        f"Fuente: {source_name}",
        "============================================================",
        "",
        "--- SECUENCIA DE SEÑAS DETECTADAS ---"
    ]

    if events:
        for ev in events:
            mins_s = int(ev.timestamp_start // 60)
            secs_s = int(ev.timestamp_start % 60)
            mins_e = int(ev.timestamp_end // 60)
            secs_e = int(ev.timestamp_end % 60)
            lines.append(f"{mins_s:02d}:{secs_s:02d} – {mins_e:02d}:{secs_e:02d} | {ev.label} (duración: {ev.duration_seconds:.1f}s)")
    else:
        lines.append("(No se detectaron señas en el archivo)")

    lines.extend([
        "",
        "--- TRADUCCIÓN BILINGÜE CONSOLIDADA ---",
        f"Español: {es_translation or '...'}",
        f"English: {en_translation or '...'}",
        "",
        "============================================================"
    ])
    return "\n".join(lines)
