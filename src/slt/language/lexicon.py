"""Bilingual Lexicon loader and resolver."""
from __future__ import annotations
import json
import unicodedata
from pathlib import Path

def normalize_gloss(g: str) -> str:
    """Normalize gloss name to uppercase ASCII without punctuation."""
    norm = unicodedata.normalize("NFKD", str(g)).encode("ascii", "ignore").decode()
    return "_".join(norm.upper().split())

class Lexicon:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"No se encontró el lexicón: {self.path}")

        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.words = {}
        for k, v in data.get("words", {}).items():
            self.words[normalize_gloss(k)] = v

        self.phrases = []
        for p in data.get("phrases", []):
            gloss_tuple = tuple(normalize_gloss(g) for g in p.get("glosses", []))
            self.phrases.append((gloss_tuple, p))

        # Sort phrases longest first for greedy matching
        self.phrases.sort(key=lambda x: -len(x[0]))

    def get_sign(self, gloss: str) -> dict | None:
        return self.words.get(normalize_gloss(gloss))

    def get_word(self, gloss: str, lang: str = "es", person: str = "1") -> str:
        w = self.get_sign(gloss)
        if not w:
            return gloss.lower().replace("_", " ")

        if w.get("type") == "letter":
            return gloss.lower()

        val = w.get(lang)
        if isinstance(val, dict):
            return val.get(str(person), val.get("1", ""))
        return str(val) if val is not None else gloss.lower()

    def get_guide(self, gloss: str) -> str:
        w = self.get_sign(gloss)
        if w and "guide" in w:
            return w["guide"]
        return "Realiza la configuración manual correspondiente a esta seña."
