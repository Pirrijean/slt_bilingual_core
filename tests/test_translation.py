"""Unit tests for bilingual translation engine."""
import pytest
from slt.language.translator import BilingualTranslator
from slt.utils.paths import LEXICON_PATH

@pytest.fixture
def translator():
    return BilingualTranslator(LEXICON_PATH)

def test_greeting_rule(translator):
    res = translator.translate_glosses(["HOLA", "TU"])
    assert "¡Hola! ¿Cómo estás?" in res["es"]
    assert "Hello! How are you?" in res["en"]

def test_need_water_rule(translator):
    res = translator.translate_glosses(["YO", "QUERER", "AGUA"])
    assert "Yo quiero agua, por favor." in res["es"]
    assert "I want water, please." in res["en"]

def test_urgent_help_rule(translator):
    res = translator.translate_glosses(["YO", "AYUDA"])
    assert "¡Necesito ayuda urgente!" in res["es"]
    assert "I need urgent help!" in res["en"]

def test_polite_yes_no(translator):
    res_yes = translator.translate_glosses(["SI", "GRACIAS"])
    assert "Sí, muchas gracias." in res_yes["es"]
    assert "Yes, thank you very much." in res_yes["en"]

    res_no = translator.translate_glosses(["NO", "GRACIAS"])
    assert "No, muchas gracias." in res_no["es"]
    assert "No, thank you very much." in res_no["en"]

def test_fingerspelling_assembly(translator):
    res = translator.translate_glosses(["H", "O", "L", "A"])
    assert res["es"] == "Hola."
    assert res["en"] == "Hola."

def test_empty_or_nada(translator):
    res = translator.translate_glosses(["_NADA_"])
    assert res["es"] == ""
    assert res["en"] == ""

def test_accumulator_operations(translator):
    translator.clear_sentence()
    translator.add_gloss("YO")
    translator.add_gloss("ESTAR_BIEN")
    res = translator.get_translation()
    assert "Yo estoy muy bien." in res["es"]
    assert "I am doing well." in res["en"]

    translator.remove_last_gloss()
    res2 = translator.get_translation()
    assert res2["glosses"] == ["YO"]

    translator.clear_sentence()
    assert translator.get_translation()["glosses"] == []
