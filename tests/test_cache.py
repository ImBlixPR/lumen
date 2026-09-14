from lumen.pipeline.cache import CacheStore, book_key, cache_path
from lumen.pipeline.sentences import Sentence


def test_commit_coverage_and_subtitles(tmp_path):
    db = CacheStore(tmp_path / "b.sqlite")
    rows = db.commit(0, 30, [Sentence(0, 5, "Hola."), Sentence(6, 12, "Adiós.")])
    db.commit(30, 60, [Sentence(31, 40, "Otra.")])
    assert db.coverage() == [(0, 60)]

    db.save_translations([(rows[0].id, "مرحبا.")], "ar", "nllb")
    subs = db.subtitles("ar", "nllb")
    assert [x.text for x in subs] == ["مرحبا.", None, None]
    assert [x.text for x in db.untranslated("ar", "nllb")] == ["Adiós.", "Otra."]
    assert db.translated_count("ar", "nllb") == (1, 3)


def test_language_switch_reuses_transcript(tmp_path):
    db = CacheStore(tmp_path / "b.sqlite")
    (row,) = db.commit(0, 10, [Sentence(0, 5, "Hola.")])
    db.save_translations([(row.id, "مرحبا.")], "ar", "nllb")
    assert [x.text for x in db.untranslated("fr", "nllb")] == ["Hola."]
    assert db.untranslated("ar", "nllb") == []


def test_recommit_replaces_overlapping_sentences_and_translations(tmp_path):
    db = CacheStore(tmp_path / "b.sqlite")
    (frag,) = db.commit(100, 110, [Sentence(100, 104, "fragmento.")])
    db.save_translations([(frag.id, "جزء.")], "ar", "nllb")
    db.commit(0, 105, [Sentence(95, 104, "Frase completa.")])
    assert [x.text for x in db.subtitles("ar", "nllb")] == [None]
    assert db.sentences_between(0, 200)[0].text == "Frase completa."
    assert db.coverage() == [(0, 110)]


def test_reopen_loads_from_disk(tmp_path):
    path = tmp_path / "b.sqlite"
    db = CacheStore(path)
    db.commit(0, 10, [Sentence(1, 2, "Hola.")])
    db.close()
    again = CacheStore(path)
    assert again.coverage() == [(0, 10)]
    assert len(again.subtitles("ar", "nllb")) == 1


def test_outdated_transcripts_are_discarded(tmp_path, monkeypatch):
    import lumen.pipeline.cache as cache_module

    path = tmp_path / "b.sqlite"
    db = CacheStore(path)
    (row,) = db.commit(0, 10, [Sentence(0, 5, "Hola.")])
    db.save_translations([(row.id, "مرحبا.")], "ar", "nllb")
    db.close()

    monkeypatch.setattr(cache_module, "TRANSCRIPT_VERSION", "999")
    newer = CacheStore(path)
    assert newer.coverage() == []
    assert newer.subtitles("ar", "nllb") == []
    assert newer.get_meta("transcript") == "999"


def test_changing_the_hint_redoes_the_transcript(tmp_path):
    db = CacheStore(tmp_path / "b.sqlite")
    db.ensure_hint("Book.")
    (row,) = db.commit(0, 10, [Sentence(0, 5, "Hola.")])
    db.save_translations([(row.id, "مرحبا.")], "ar", "nllb")

    db.ensure_hint("Book.")  # same hint: keep everything
    assert db.coverage() == [(0, 10)]

    db.ensure_hint("Book. Ernest, Célestine.")  # names added: transcribe again
    assert db.coverage() == []
    assert db.subtitles("ar", "nllb") == []
    assert db.get_meta("hint") == "Book. Ernest, Célestine."


def test_untranslated_prioritises_near_playhead(tmp_path):
    db = CacheStore(tmp_path / "b.sqlite")
    db.commit(0, 100, [Sentence(t, t + 1, f"s{t}.") for t in (10, 50, 90)])
    assert [x.text for x in db.untranslated("ar", "nllb", near=40)] == ["s50.", "s90.", "s10."]


def test_book_key_is_content_based(tmp_path):
    a = tmp_path / "a.mp3"
    a.write_bytes(b"x" * 3_000_000)
    b = tmp_path / "renamed.mp3"
    b.write_bytes(b"x" * 3_000_000)
    assert book_key(a) == book_key(b)
    a.write_bytes(b"y" + b"x" * 2_999_999)
    assert book_key(a) != book_key(b)
    assert cache_path(tmp_path, "k", "es", "large-v3").name == "k-es-large-v3.sqlite"
