"""Merge Whisper word timings into complete sentences.

Translation quality drops sharply on fragments, so every subtitle is one whole sentence.
The rules:
- Split after terminal punctuation, except after abbreviations ("Sr. García") and when the
  next word starts lowercase, which marks a dialogue tag ("—¿Vienes? —preguntó él.") or a
  mid-sentence ellipsis.
- Always split on a long pause. Audiobook headings ("Capítulo uno") carry no punctuation.
- Force-split only runaway sentences, preferring commas and pauses near the middle.
- Fold one-word fragments into a neighbour.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

TERMINATORS = frozenset(".!?…。！？؟۔।")
SOFT_BREAKS = frozenset(",;:،、，；：—–")
CLOSERS = "\"'»”’)]}›」』"
OPENERS = "\"'«“‘¿¡([{‹「『—–-"

ABBREVIATIONS: dict[str, frozenset[str]] = {
    "es": frozenset("sr sra srta dr dra d dña ud uds lic prof pág núm av aprox cap vs".split()),
    "en": frozenset("mr mrs ms dr prof st jr sr vs mt gen col lt capt sgt rev hon fig".split()),
    "fr": frozenset("m mme mlle mm dr st ste prof".split()),
    "de": frozenset("hr fr dr prof nr bzw ca evtl ggf vgl".split()),
    "it": frozenset("sig sigra dott prof avv ing".split()),
    "pt": frozenset("sr sra dr dra prof av".split()),
    "nl": frozenset("dhr mevr dr prof".split()),
}

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class Word:
    start: float
    end: float
    text: str  # as emitted by Whisper, including any leading space


@dataclass(frozen=True, slots=True)
class Sentence:
    start: float
    end: float
    text: str


def _core(token: str) -> str:
    return token.strip().rstrip(CLOSERS)


def _first_letter(token: str) -> str:
    for ch in token.strip():
        if ch.isalnum():
            return ch
    return ""


def _is_abbreviation(token: str, lang: str) -> bool:
    core = _core(token).lstrip(OPENERS)
    if not core.endswith(".") or core.endswith(".."):
        return False
    body = core[:-1]
    if len(body) == 1 and body.isalpha() and body.isupper():
        return True  # an initial, as in "J. R. R. Tolkien"
    if "." in body:
        return True  # dotted forms: "EE.UU.", "z.B."
    return body.lower() in ABBREVIATIONS.get(lang, frozenset())


def ends_sentence(word: Word, next_word: Word | None, lang: str) -> bool:
    core = _core(word.text)
    if not core or core[-1] not in TERMINATORS:
        return False
    if core[-1] == "." and _is_abbreviation(word.text, lang):
        return False
    if next_word is None:
        return True
    first = _first_letter(next_word.text)
    # Uncased scripts (Arabic, CJK, Thai...) report neither lower nor upper, so they split.
    return not (first and first.islower())


def _duration(group: Sequence[Word]) -> float:
    return group[-1].end - group[0].start


def _chars(group: Sequence[Word]) -> int:
    return len("".join(w.text for w in group).strip())


def _split_long(group: list[Word], max_duration: float, max_chars: int) -> list[list[Word]]:
    # Long runs are split at the best comma or pause: they overflow the subtitle, and NLLB
    # silently drops the tail of long inputs (seen in testing on comma-chained dialogue).
    if len(group) < 2 or (_duration(group) <= max_duration and _chars(group) <= max_chars):
        return [group]
    span = _duration(group)
    mid = group[0].start + span / 2
    best_index, best_score = 0, float("-inf")
    for i in range(len(group) - 1):
        word, nxt = group[i], group[i + 1]
        core = _core(word.text)
        punct = 0.0
        if core and core[-1] in TERMINATORS:
            punct = 1.5
        elif core and core[-1] in SOFT_BREAKS:
            punct = 1.0
        gap = min(max(0.0, nxt.start - word.end), 1.5)
        centrality = 1.0 - abs(word.end - mid) / (span / 2)
        score = 2.0 * punct + gap + centrality
        if score > best_score:
            best_index, best_score = i, score
    left, right = group[: best_index + 1], group[best_index + 1 :]
    return _split_long(left, max_duration, max_chars) + _split_long(right, max_duration, max_chars)


def _is_fragment(group: Sequence[Word], min_duration: float) -> bool:
    if len(group) != 1 or _duration(group) >= min_duration:
        return False
    core = _core(group[0].text)
    return not (core and core[-1] in TERMINATORS)


def _continues(group: Sequence[Word]) -> bool:
    """True if the group starts lowercase, i.e. it carries on a sentence begun earlier."""
    first = _first_letter(group[0].text)
    return bool(first) and first.islower()


def _merge_fragments(groups: list[list[Word]], min_duration: float, max_gap: float = 1.5) -> list[list[Word]]:
    result: list[list[Word]] = []
    pending: list[Word] = []
    for group in groups:
        if pending:
            if group[0].start - pending[-1].end < max_gap:
                group = pending + group
            elif _continues(group):
                # The fragment begins a sentence that resumes after a long pause ("Il" … music …
                # "n'y a plus qu'à…"). Whisper misplaced its timestamp, so it joins the sentence
                # at the sentence's own start instead of hanging alone over the music.
                group = [Word(group[0].start, group[0].start, w.text) for w in pending] + group
            else:
                result.append(pending)
            pending = []
        if _is_fragment(group, min_duration):
            pending = group
            continue
        result.append(group)
    if pending:
        if result and pending[0].start - result[-1][-1].end < max_gap:
            result[-1] = result[-1] + pending
        else:
            result.append(pending)
    return result


def _to_sentence(group: Sequence[Word]) -> Sentence:
    text = _WHITESPACE.sub(" ", "".join(w.text for w in group)).strip()
    return Sentence(group[0].start, group[-1].end, text)


def build_sentences(
    words: Sequence[Word],
    lang: str,
    *,
    max_duration: float = 8.0,
    max_chars: int = 110,
    pause_split: float = 2.0,
    min_duration: float = 0.6,
) -> list[Sentence]:
    """Group timed words into sentences ready for translation."""
    tokens = [w for w in words if w.text.strip()]
    groups: list[list[Word]] = []
    current: list[Word] = []
    for i, word in enumerate(tokens):
        if current and word.start - current[-1].end >= pause_split:
            groups.append(current)
            current = []
        current.append(word)
        next_word = tokens[i + 1] if i + 1 < len(tokens) else None
        if ends_sentence(word, next_word, lang):
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    split = [part for group in groups for part in _split_long(group, max_duration, max_chars)]
    return [_to_sentence(g) for g in _merge_fragments(split, min_duration)]
