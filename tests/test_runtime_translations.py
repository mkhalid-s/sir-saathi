import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.translations import resolve_locale, translate_message


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_repository_runtime_falls_back_from_planned_or_unknown_locales() -> None:
    assert resolve_locale("en").fallback is False
    assert resolve_locale("mr").used == "en"
    assert resolve_locale("mr").fallback is True
    assert resolve_locale("zz").used == "en"


def test_runtime_uses_only_a_complete_reviewed_catalogue(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalogues = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "available"},
    ]})
    _write(catalogues / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}"},
    })
    _write(catalogues / "mr.json", {
        "schema_version": 1,
        "locale": "mr",
        "review": {
            "status": "reviewed",
            "translated_by": "fixture translator",
            "reviewed_by": "fixture reviewer",
            "reviewed_at": "2026-08-01",
        },
        "messages": {"hello": "नमस्कार {name}"},
    })

    resolved = resolve_locale("mr", locales_path=locales, catalog_dir=catalogues)
    assert resolved.used == "mr"
    assert resolved.fallback is False
    assert translate_message(
        "mr", "hello", {"name": "साथी"}, locales_path=locales, catalog_dir=catalogues
    ) == "नमस्कार साथी"
    with pytest.raises(ValueError, match="missing translation value"):
        translate_message("mr", "hello", locales_path=locales, catalog_dir=catalogues)
