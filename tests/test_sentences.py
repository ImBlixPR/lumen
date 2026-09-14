from lumen.pipeline.sentences import Word, build_sentences


def words(text: str, start: float = 0.0, step: float = 0.4, gaps: dict[int, float] | None = None):
    """Whisper-style words (leading spaces), each `step` long, with optional extra gaps before index i."""
    gaps = gaps or {}
    out, t = [], start
    for i, token in enumerate(text.split()):
        t += gaps.get(i, 0.0)
        out.append(Word(t, t + step, " " + token))
        t += step
    return out


def texts(ws, lang="es", **kw):
    return [s.text for s in build_sentences(ws, lang, **kw)]


def test_splits_on_terminal_punctuation():
    assert texts(words("Hola mundo. Esto es una prueba.")) == ["Hola mundo.", "Esto es una prueba."]


def test_abbreviation_does_not_split():
    assert texts(words("El Sr. García llegó tarde. Nadie habló.")) == [
        "El Sr. García llegó tarde.",
        "Nadie habló.",
    ]


def test_initials_do_not_split():
    assert texts(words("Lo escribió J. R. Tolkien hace años."), lang="en") == [
        "Lo escribió J. R. Tolkien hace años."
    ]


def test_spanish_dialogue_tag_stays_with_quote():
    result = texts(words("—¿Vienes conmigo? —preguntó ella. —Sí."))
    assert result == ["—¿Vienes conmigo? —preguntó ella.", "—Sí."]


def test_mid_sentence_ellipsis_continues():
    assert texts(words("Pensó… y luego se fue. Fin.")) == ["Pensó… y luego se fue.", "Fin."]


def test_long_pause_splits_unpunctuated_heading():
    ws = words("Capítulo uno Era una noche oscura.", gaps={2: 3.0})
    assert texts(ws) == ["Capítulo uno", "Era una noche oscura."]


def test_french_spaced_punctuation_and_guillemets():
    # French puts a space before ! ? : ; so Whisper often emits the mark as its own word.
    ws = words("Bonjour ! Comment vas-tu ? « Très bien », répondit M. Dupont.")
    assert texts(ws, lang="fr") == [
        "Bonjour !",
        "Comment vas-tu ?",
        "« Très bien », répondit M. Dupont.",
    ]


def test_uncased_script_splits_after_arabic_question_mark():
    assert texts(words("هل أنت هنا؟ نعم أنا هنا."), lang="ar") == ["هل أنت هنا؟", "نعم أنا هنا."]


def test_runaway_sentence_is_force_split_at_comma():
    first = " ".join(["uno"] * 24) + ","
    second = " ".join(["dos"] * 24) + "."
    sentences = build_sentences(words(f"{first} {second}", step=0.5), "es", max_duration=18.0)
    assert len(sentences) >= 2
    assert sentences[0].text.endswith(",")
    assert all(s.end - s.start <= 18.0 for s in sentences)


def test_comma_chained_dialogue_is_split_into_readable_pieces():
    # Real Whisper output from the test book: one 12 s "sentence" joined by commas.
    text = ("non mais regarde moi Ernest, j'ai que la peau sur les os, et puis c'est très mauvais "
            "pour ta santé de manger dans les poubelles, il y a toutes les maladies du monde dans "
            "une poubelle, il y a la grippe, le typhus, l'hépatite, le choléra, Ernest, tu veux "
            "attraper toutes les maladies du monde ?")
    sentences = build_sentences(words(text, step=0.25), "fr")
    assert len(sentences) >= 3
    assert all(len(s.text) <= 110 and s.end - s.start <= 8.0 for s in sentences)
    assert all(s.text.endswith((",", "?")) for s in sentences)  # cut at commas, not mid-phrase
    assert " ".join(s.text for s in sentences) == text


def test_single_word_fragment_merges_into_next():
    # A fragment split off by a short pause folds into the following sentence.
    ws = [Word(0.0, 0.3, " Y"), Word(0.8, 1.2, " entonces"), Word(1.2, 1.6, " llovió.")]
    assert texts(ws, pause_split=0.4) == ["Y entonces llovió."]


def test_fragment_far_from_neighbours_stays_alone():
    ws = [Word(0.0, 0.3, " Y"), Word(4.0, 4.4, " Entonces"), Word(4.4, 4.8, " llovió.")]
    assert texts(ws) == ["Y", "Entonces llovió."]


def test_misplaced_first_word_joins_its_sentence_after_music():
    # Real case from the test book: Whisper put "Il" 15 s before the rest of its sentence.
    ws = [Word(113.11, 113.13, " Il"), Word(128.97, 129.3, " n'y"), Word(129.3, 129.5, " a"),
          Word(129.5, 129.8, " plus"), Word(129.8, 130.1, " qu'à"), Word(130.1, 130.4, " se"),
          Word(130.4, 130.9, " servir.")]
    sentences = build_sentences(ws, "fr")
    assert [s.text for s in sentences] == ["Il n'y a plus qu'à se servir."]
    assert sentences[0].start == 128.97  # shown when it's spoken, not during the music


def test_timestamps_span_words():
    s = build_sentences(words("Una frase completa.", start=10.0), "es")[0]
    assert s.start == 10.0
    assert abs(s.end - 11.2) < 1e-9
