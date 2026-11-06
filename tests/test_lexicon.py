"""Unit tests verifying lexicon integrity and class completeness."""
import json
from slt.language.lexicon import Lexicon
from slt.utils.paths import LEXICON_PATH, CLASSES_PATH

def test_lexicon_loads_and_contains_classes():
    with open(CLASSES_PATH, "r", encoding="utf-8") as f:
        classes = json.load(f)["classes"]

    lex = Lexicon(LEXICON_PATH)

    for c in classes:
        if c == "_NADA_":
            continue
        sign_info = lex.get_sign(c)
        assert sign_info is not None, f"Seña '{c}' declarada en classes.json pero no existe en lexicon.json"

        # Check guides exist
        guide = lex.get_guide(c)
        assert len(guide) > 5, f"Guía para '{c}' está vacía"
