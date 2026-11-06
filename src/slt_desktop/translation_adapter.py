#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLT Desktop: Translation Adapter Module.
Translates recognized sign glosses into simultaneous natural Spanish and English utterances.
"""
from typing import List, Dict, Optional
import logging

from slt.language import BilingualTranslator, Lexicon

logger = logging.getLogger("slt_desktop.translation_adapter")


class TranslationAdapter:
    """
    Adapter interfacing the desktop UI with the bilingual linguistic engine.
    Produces synchronized Spanish and English translations from gloss sequences.
    """
    def __init__(self, lexicon_path: Optional[str] = None):
        self.lexicon = Lexicon(filepath=lexicon_path)
        self.translator = BilingualTranslator(lexicon=self.lexicon)

    def translate_glosses(self, glosses: List[str]) -> Dict[str, str]:
        """
        Translates a sequence of sign glosses into simultaneous sentences in Spanish and English.
        Returns:
            {"es": "...", "en": "..."}
        """
        if not glosses:
            return {"es": "", "en": ""}

        # Filter out _NADA_
        clean_glosses = [g for g in glosses if g and g != "_NADA_"]
        if not clean_glosses:
            return {"es": "", "en": ""}

        try:
            es_text, en_text = self.translator.translate(clean_glosses)
            return {"es": es_text, "en": en_text}
        except Exception as e:
            logger.error(f"Translation error: {e}")
            fallback = " ".join(clean_glosses)
            return {"es": fallback, "en": fallback}
