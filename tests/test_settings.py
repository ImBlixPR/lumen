from PySide6.QtCore import QCoreApplication

from lumen.services.settings import SettingsStore


def test_book_names_persist_per_book(tmp_path):
    _app = QCoreApplication.instance() or QCoreApplication([])
    store = SettingsStore(tmp_path)
    store.set_book_names("book-a", "Ernest, Célestine")
    store.flush()

    again = SettingsStore(tmp_path)
    assert again.book_names("book-a") == "Ernest, Célestine"
    assert again.book_names("book-b") == ""

    again.set_book_names("book-a", "")
    again.flush()
    assert SettingsStore(tmp_path).book_names("book-a") == ""
