"""Importable transliteration helpers built from the legacy CLI module."""

from __future__ import annotations

import re

from pipeline.transliterate import devanagari_to_roman, virgo_to_devanagari, virgo_to_english

DEVANAGARI_START = "\u0900"
DEVANAGARI_END = "\u097f"


def contains_devanagari(value: str) -> bool:
    return any(DEVANAGARI_START <= character <= DEVANAGARI_END for character in value)


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def searchable_name_forms(value: str | None, *, source_encoding: str | None = None) -> tuple[str, str | None]:
    """Return source-normalized and Roman search forms without guessing legacy encodings."""
    original = value or ""
    encoding = (source_encoding or "").strip().casefold()
    if encoding == "virgod3":
        roman = _normalize(virgo_to_english(original))
        return roman, roman or None
    normalized = _normalize(original)
    if contains_devanagari(original):
        roman = _normalize(devanagari_to_roman(original))
        return normalized, roman or None
    return normalized, normalized or None


__all__ = [
    "contains_devanagari",
    "devanagari_to_roman",
    "searchable_name_forms",
    "virgo_to_devanagari",
    "virgo_to_english",
]
