import pytest
from slt.language import BilingualTranslator, Lexicon, SemanticFrame

def test_lexicon_schema_and_classes():
    lexicon = Lexicon()
    assert len(lexicon.words) >= 18
    # Test schema properties on representative word
    agua = lexicon.get_word("AGUA")
    assert agua is not None
    assert agua.get("semantic_id") == "WATER"
    assert agua.get("syntactic_role") == "object"
    assert agua.get("validation_status") == "validated"

def test_semantic_frame_parsing():
    translator = BilingualTranslator()
    frame = translator.parse_semantic_frame(["YO", "QUERER", "AGUA"])
    assert frame.subject == "FIRST_PERSON"
    assert frame.action == "WANT"
    assert frame.object == "WATER"
    assert frame.polarity == "positive"

def test_greeting_and_courtesy_translation():
    translator = BilingualTranslator()
    es, en = translator.translate(["HOLA", "TU"])
    assert "¡Hola!" in es
    assert "Hello!" in en

    es_polite, en_polite = translator.translate(["SI", "POR_FAVOR"])
    assert es_polite == "Sí, por favor."
    assert en_polite == "Yes, please."

def test_pro_drop_and_english_subject():
    translator = BilingualTranslator()
    es, en = translator.translate(["YO", "QUERER", "AGUA"])
    assert "agua" in es.lower()
    assert "I want water" in en

def test_dactilology_fingerspelling_assembly():
    translator = BilingualTranslator()
    es, en = translator.translate(["A", "E", "I"])
    assert "AEI" in es
    assert "AEI" in en

def test_accumulator_operations():
    translator = BilingualTranslator()
    translator.add_gloss("HOLA")
    translator.add_gloss("GRACIAS")
    assert len(translator.gloss_buffer) == 2
    translator.remove_last_gloss()
    assert translator.gloss_buffer == ["HOLA"]
    translator.clear()
    assert len(translator.gloss_buffer) == 0
