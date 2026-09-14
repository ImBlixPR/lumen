"""Languages supported by both Whisper (speech) and NLLB-200 (translation).

Whisper identifies languages by ISO 639-1 codes; NLLB uses FLORES-200 codes. Settings store
the Whisper code and translate on demand, so neither language is ever hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Language:
    code: str  # Whisper / ISO 639-1
    flores: str  # NLLB-200
    name: str  # English name
    native: str  # endonym, shown next to the English name in pickers
    rtl: bool = False


LANGUAGES: tuple[Language, ...] = (
    Language("ar", "arb_Arab", "Arabic", "العربية", rtl=True),
    Language("bn", "ben_Beng", "Bengali", "বাংলা"),
    Language("ca", "cat_Latn", "Catalan", "Català"),
    Language("cs", "ces_Latn", "Czech", "Čeština"),
    Language("da", "dan_Latn", "Danish", "Dansk"),
    Language("de", "deu_Latn", "German", "Deutsch"),
    Language("el", "ell_Grek", "Greek", "Ελληνικά"),
    Language("en", "eng_Latn", "English", "English"),
    Language("es", "spa_Latn", "Spanish", "Español"),
    Language("fa", "pes_Arab", "Persian", "فارسی", rtl=True),
    Language("fi", "fin_Latn", "Finnish", "Suomi"),
    Language("fr", "fra_Latn", "French", "Français"),
    Language("he", "heb_Hebr", "Hebrew", "עברית", rtl=True),
    Language("hi", "hin_Deva", "Hindi", "हिन्दी"),
    Language("hu", "hun_Latn", "Hungarian", "Magyar"),
    Language("id", "ind_Latn", "Indonesian", "Bahasa Indonesia"),
    Language("it", "ita_Latn", "Italian", "Italiano"),
    Language("ja", "jpn_Jpan", "Japanese", "日本語"),
    Language("ko", "kor_Hang", "Korean", "한국어"),
    Language("ms", "zsm_Latn", "Malay", "Bahasa Melayu"),
    Language("nl", "nld_Latn", "Dutch", "Nederlands"),
    Language("no", "nob_Latn", "Norwegian", "Norsk"),
    Language("pl", "pol_Latn", "Polish", "Polski"),
    Language("pt", "por_Latn", "Portuguese", "Português"),
    Language("ro", "ron_Latn", "Romanian", "Română"),
    Language("ru", "rus_Cyrl", "Russian", "Русский"),
    Language("sv", "swe_Latn", "Swedish", "Svenska"),
    Language("sw", "swh_Latn", "Swahili", "Kiswahili"),
    Language("th", "tha_Thai", "Thai", "ไทย"),
    Language("tr", "tur_Latn", "Turkish", "Türkçe"),
    Language("uk", "ukr_Cyrl", "Ukrainian", "Українська"),
    Language("ur", "urd_Arab", "Urdu", "اردو", rtl=True),
    Language("vi", "vie_Latn", "Vietnamese", "Tiếng Việt"),
    Language("zh", "zho_Hans", "Chinese (Simplified)", "中文"),
)

_BY_CODE = {lang.code: lang for lang in LANGUAGES}


def get(code: str) -> Language:
    """Return the language for a Whisper code, raising KeyError for unsupported codes."""
    return _BY_CODE[code]


def is_supported(code: str) -> bool:
    return code in _BY_CODE


def flores(code: str) -> str:
    return _BY_CODE[code].flores


def is_rtl(code: str) -> bool:
    lang = _BY_CODE.get(code)
    return bool(lang and lang.rtl)
