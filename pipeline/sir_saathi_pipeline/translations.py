"""Runtime access to fail-closed, human-reviewed message catalogues."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from .translation_catalog import (
    DEFAULT_CATALOG_DIR,
    DEFAULT_LOCALES_PATH,
    PLACEHOLDER_PATTERN,
    translation_readiness,
)


@dataclass(frozen=True)
class LocaleResolution:
    requested: str
    used: str
    fallback: bool


@lru_cache(maxsize=8)
def _runtime_catalogues(
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> tuple[dict[str, dict[str, str]], frozenset[str]]:
    report = translation_readiness(locales_path=locales_path, catalog_dir=catalog_dir)
    publishable = frozenset(report["available_locales"])
    catalogues: dict[str, dict[str, str]] = {}
    for locale in publishable:
        path = catalog_dir / f"{locale}.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        catalogues[locale] = payload["messages"]
    return catalogues, publishable


def resolve_locale(
    requested: str | None,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> LocaleResolution:
    normalized = (requested or "en").strip().lower()
    catalogues, publishable = _runtime_catalogues(locales_path, catalog_dir)
    del catalogues
    used = normalized if normalized in publishable else "en"
    return LocaleResolution(requested=normalized, used=used, fallback=used != normalized)


def translate_message(
    locale: str,
    key: str,
    values: dict[str, Any] | None = None,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> str:
    catalogues, publishable = _runtime_catalogues(locales_path, catalog_dir)
    if locale not in publishable:
        raise ValueError(f"locale is not publishable: {locale}")
    messages = catalogues[locale]
    if key not in messages:
        raise KeyError(f"unknown translation key: {key}")
    replacements = values or {}

    def replace(match) -> str:
        name = match.group(1)
        if name not in replacements:
            raise ValueError(f"missing translation value: {name}")
        return str(replacements[name])

    return PLACEHOLDER_PATTERN.sub(replace, messages[key])
