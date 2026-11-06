#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Translation Adapter Module.
Translates recognized sign glosses into simultaneous natural Spanish and English utterances.
"""
from __future__ import annotations
from typing import Optional, List, Dict
import logging

from slt.language import BilingualTranslator, Lexicon

logger = logging.getLogger("slt_desktop.translation_adapter")


class DefaultTranslationService:
    """Wrapper around the core BilingualTranslator conforming to translate_glosses contract."""
    def __init__(self, lexicon_path: Optional[str] = None):
        self.lexicon = Lexicon(filepath=lexicon_path)
        self.translator = BilingualTranslator(lexicon=self.lexicon)

    def translate_glosses(self, glosses: list[str]) -> dict:
        clean = [g for g in glosses if g and g != "_NADA_"]
        if not clean:
            return {"es": "", "en": ""}
        try:
            es_text, en_text = self.translator.translate(clean)
            return {"es": es_text, "en": en_text}
        except Exception as e:
            logger.error(f"Translation error: {e}")
            fallback = " ".join(clean)
            return {"es": fallback, "en": fallback}


class TranslationAdapter:
    """
    Adapter interfacing the desktop UI with the bilingual linguistic engine.
    Produces synchronized Spanish and English translations from gloss sequences.
    """
    def __init__(self, implementation=None):
        if implementation is None:
            try:
                self.implementation = DefaultTranslationService()
            except Exception as e:
                logger.warning(f"Failed to load default translation service: {e}")
                self.implementation = None
        else:
            self.implementation = implementation

    @property
    def ready(self) -> bool:
        return self.implementation is not None

    def translate_glosses(self, glosses: list[str]) -> dict:
        if not self.ready:
            return {
                "es": "",
                "en": ""
            }
        return self.implementation.translate_glosses(glosses)
