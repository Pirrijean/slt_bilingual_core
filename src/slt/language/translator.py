"""Bilingual Translator with sentence accumulator."""
from __future__ import annotations
from pathlib import Path
from .lexicon import Lexicon, normalize_gloss
from .sentence_builder import SentenceBuilder

class BilingualTranslator:
    """
    Coordinates bilingual sign translation and state accumulation.
    Maintains a buffer of confirmed glosses and formats concurrent outputs in ES & EN.
    """
    def __init__(self, lexicon_path: str | Path):
        self.lexicon = Lexicon(lexicon_path)
        self.builder = SentenceBuilder(self.lexicon)
        self.gloss_buffer: list[str] = []

    def add_gloss(self, gloss: str) -> dict[str, str]:
        """Add a confirmed gloss and return updated translation."""
        norm = normalize_gloss(gloss)
        if norm and norm != "_NADA_":
            self.gloss_buffer.append(norm)
        return self.get_translation()

    def remove_last_gloss(self) -> dict[str, str]:
        """Undo last confirmed gloss."""
        if self.gloss_buffer:
            self.gloss_buffer.pop()
        return self.get_translation()

    def clear_sentence(self) -> dict[str, str]:
        """Reset current sentence accumulator."""
        self.gloss_buffer.clear()
        return {"glosses": [], "es": "", "en": ""}

    def get_translation(self) -> dict[str, str]:
        """Get current translations for accumulated gloss buffer."""
        return {
            "glosses": list(self.gloss_buffer),
            "es": self.builder.build_sentence(self.gloss_buffer, "es"),
            "en": self.builder.build_sentence(self.gloss_buffer, "en"),
        }

    def translate_glosses(self, glosses: list[str]) -> dict[str, str]:
        """Translate an arbitrary list of glosses without affecting internal buffer."""
        clean = [normalize_gloss(g) for g in glosses if g and normalize_gloss(g) != "_NADA_"]
        return {
            "glosses": clean,
            "es": self.builder.build_sentence(clean, "es"),
            "en": self.builder.build_sentence(clean, "en"),
        }
