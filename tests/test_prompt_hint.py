from lumen.pipeline.worker import normalize_names, prompt_hint


def test_names_join_the_hint():
    assert prompt_hint("ERNEST & CELESTINE", "Ernest, Célestine") == "Ernest & Celestine. Ernest, Célestine."
    assert prompt_hint("", "Ernest") == "Ernest."
    assert prompt_hint("Le Petit Prince", "") == "Le Petit Prince."


def test_normalize_names():
    assert normalize_names(" Ernest ,Célestine\nernest;; Léon ") == ["Ernest", "Célestine", "Léon"]
    assert normalize_names("") == []
    assert normalize_names(",, ;") == []


def test_all_caps_words_are_title_cased():
    assert prompt_hint("ERNEST & CELESTINE - La rencontre - Lambert Wilson") == (
        "Ernest & Celestine - La rencontre - Lambert Wilson."
    )


def test_normal_titles_are_kept():
    assert prompt_hint("Le Petit Prince") == "Le Petit Prince."
    assert prompt_hint("Où es-tu ?") == "Où es-tu ?"


def test_empty_title_gives_no_hint():
    assert prompt_hint("") == ""
    assert prompt_hint("   ") == ""
