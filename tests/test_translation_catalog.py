import json
from pathlib import Path

from pipeline.sir_saathi_pipeline.translation_catalog import main, translation_readiness


def _write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_repository_translation_readiness_is_fail_closed() -> None:
    report = translation_readiness()
    assert report["locale_count"] == 17
    assert report["available_locales"] == ["en"]
    assert report["required_message_count"] >= 20
    marathi = next(item for item in report["locales"] if item["locale"] == "mr")
    assert marathi["publishable"] is False
    assert marathi["blockers"] == ["catalogue file is missing"]


def test_translation_requires_exact_keys_placeholders_and_human_review(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "status": "available"},
        {"code": "mr", "label": "Marathi", "status": "available"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}", "safety.notice": "Check official sources"},
    })
    _write(catalog_dir / "mr.json", {
        "schema_version": 1,
        "locale": "mr",
        "review": {"status": "draft"},
        "messages": {"hello": "नमस्कार", "unexpected": "अतिरिक्त"},
    })
    marathi = translation_readiness(locales_path=locales, catalog_dir=catalog_dir)["locales"][1]
    assert marathi["publishable"] is False
    assert "missing 1 message keys" in marathi["blockers"]
    assert "contains 1 unknown message keys" in marathi["blockers"]
    assert "placeholder mismatch for hello" in marathi["blockers"]
    assert "fluent human review is required" in marathi["blockers"]
    assert "registry marks locale available before catalogue readiness" in marathi["blockers"]


def test_complete_reviewed_translation_can_be_promoted(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "status": "available"},
        {"code": "mr", "label": "Marathi", "status": "available"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}"},
    })
    _write(catalog_dir / "mr.json", {
        "schema_version": 1,
        "locale": "mr",
        "review": {"status": "reviewed", "reviewed_by": "language reviewer", "reviewed_at": "2026-08-01"},
        "messages": {"hello": "नमस्कार {name}"},
    })
    report = translation_readiness(locales_path=locales, catalog_dir=catalog_dir)
    assert report["available_locales"] == ["en", "mr"]
    assert report["locales"][1]["blockers"] == []


def test_cli_fails_when_an_available_locale_is_invalid(tmp_path: Path, capsys) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [{"code": "en", "label": "English", "status": "available"}]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "draft"},
        "messages": {"hello": "Hello"},
    })
    assert main(["--locales", str(locales), "--catalog-dir", str(catalog_dir), "--fail-on-invalid-available"]) == 1
    assert '"publishable": false' in capsys.readouterr().out
