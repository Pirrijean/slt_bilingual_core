from slt.language import BilingualTranslator, Lexicon


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


def test_srt_generation_and_formatting():
    from slt.interaction import SignEvent
    from slt.language import format_srt_time, generate_srt, generate_transcription_txt

    assert format_srt_time(0.0) == "00:00:00,000"
    assert format_srt_time(62.5) == "00:01:02,500"

    ev1 = SignEvent("e1", "YO", 1.0, 2.5, 0.95)
    ev2 = SignEvent("e2", "AGUA", 3.0, 4.2, 0.98)
    srts = generate_srt([ev1, ev2], "Yo quiero agua.", "I want water.")

    assert "bilingual" in srts
    assert "00:00:01,000 --> 00:00:04,200" in srts["bilingual"]
    assert "ES: Yo quiero agua." in srts["bilingual"]
    assert "EN: I want water." in srts["bilingual"]

    txt = generate_transcription_txt([ev1, ev2], "Yo quiero agua.", "I want water.", "test.mp4")
    assert "test.mp4" in txt
    assert "YO" in txt
    assert "AGUA" in txt
    assert "Español: Yo quiero agua." in txt
