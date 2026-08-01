import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.translations import locale_status_payload, resolve_locale, translate_message


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_repository_runtime_falls_back_from_planned_or_unknown_locales() -> None:
    assert resolve_locale("en").fallback is False
    assert resolve_locale("mr").used == "en"
    assert resolve_locale("mr").fallback is True
    assert resolve_locale("zz").used == "en"


def test_public_locale_status_is_complete_and_redacts_review_details() -> None:
    payload = locale_status_payload()
    assert payload["locale_count"] == 24
    assert payload["available_count"] == 1
    assert payload["planned_or_blocked_count"] == 23
    assert payload["values_redacted"] is True
    assert {item["code"] for item in payload["locales"]} == {
        "en", "as", "bn", "gu", "hi", "kn", "kok", "lus", "ml", "mni",
        "mr", "ne", "or", "pa", "ta", "te", "ur", "brx", "doi", "ks",
        "mai", "sa", "sat", "sd",
    }
    assert payload["coverage"]["source_url"] == "https://www.legislative.gov.in/constitution-in-regional-languages"
    english = next(item for item in payload["locales"] if item["code"] == "en")
    assert english["activation_status"] == "available"
    assert english["public_route_available"] is True
    urdu = next(item for item in payload["locales"] if item["code"] == "ur")
    assert urdu["direction"] == "rtl"
    assert urdu["activation_status"] == "planned"
    assert urdu["human_review_required"] is True
    serialized = json.dumps(payload)
    assert "translated_by" not in serialized
    assert "reviewed_by" not in serialized
    assert "blockers" not in serialized


def test_invalid_available_locale_is_publicly_blocked(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalogues = tmp_path / "translations"
    _write(locales, {
        "policy": "Human review required.",
        "coverage": {"source_url": "https://example.org/fixture"},
        "locales": [
            {"code": "en", "label": "English", "direction": "ltr", "status": "available", "review": "reviewed"},
            {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "available", "review": "required"},
        ],
    })
    _write(catalogues / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello"},
    })
    payload = locale_status_payload(locales_path=locales, catalog_dir=catalogues)
    marathi = next(item for item in payload["locales"] if item["code"] == "mr")
    assert marathi["registry_status"] == "available"
    assert marathi["activation_status"] == "blocked"
    assert marathi["public_route_available"] is False


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
