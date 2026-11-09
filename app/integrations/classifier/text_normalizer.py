"""Normalisasi nama barang sebelum diklasifikasikan."""
import re

_NON_WORD = re.compile(r"[^0-9a-z&' ]+")
_SPACES = re.compile(r"\s+")


class TextNormalizer:
    def __init__(self, abbreviations: dict[str, str] | None = None):
        abbreviations = {k.lower(): v.lower() for k, v in (abbreviations or {}).items()}
        self.phrase_abbr = {k: v for k, v in abbreviations.items() if " " in k}
        self.word_abbr = {k: v for k, v in abbreviations.items() if " " not in k}

    def basic(self, text: str) -> str:
        text = _NON_WORD.sub(" ", text.lower())
        return _SPACES.sub(" ", text).strip()

    def normalize(self, text: str) -> str:
        text = f" {self.basic(text)} "
        for short, full in self.phrase_abbr.items():
            text = text.replace(f" {short} ", f" {full} ")
        words = [self.word_abbr.get(w, w) for w in text.split()]
        return " ".join(words)
