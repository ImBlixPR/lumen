import re

import pytest

from lumen import languages


def test_codes_are_unique_and_flores_well_formed():
    codes = [lang.code for lang in languages.LANGUAGES]
    assert len(codes) == len(set(codes))
    for lang in languages.LANGUAGES:
        assert re.fullmatch(r"[a-z]{3}_[A-Z][a-z]{3}", lang.flores), lang


def test_rtl_languages():
    assert {l.code for l in languages.LANGUAGES if l.rtl} == {"ar", "fa", "he", "ur"}
    assert languages.is_rtl("ar") and not languages.is_rtl("es") and not languages.is_rtl("xx")


def test_lookup():
    assert languages.flores("es") == "spa_Latn"
    assert languages.get("ar").native == "العربية"
    with pytest.raises(KeyError):
        languages.get("xx")
