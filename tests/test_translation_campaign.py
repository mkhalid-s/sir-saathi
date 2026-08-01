import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.translation_campaign import (
    ROOT,
    _safe_output_directory,
    create_campaign,
    validate_campaign,
)


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def fixture_catalogue(tmp_path: Path) -> tuple[Path, Path]:
    locales = tmp_path / "config" / "locales.json"
    catalogues = tmp_path / "config" / "translations"
    write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "hi", "label": "Hindi", "direction": "ltr", "status": "planned"},
        {"code": "ur", "label": "Urdu", "direction": "rtl", "status": "planned"},
    ]})
    write(catalogues / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}", "safety.notice": "Check official sources"},
    })
    return locales, catalogues


def test_campaign_atomically_creates_every_planned_packet(tmp_path: Path) -> None:
    locales, catalogues = fixture_catalogue(tmp_path)
    output = tmp_path / "private-campaign"
    report = create_campaign(output, locales_path=locales, catalog_dir=catalogues)
    assert report == {"written": True, "locale_count": 2, "message_count": 2, "values_redacted": True}
    assert {path.name for path in output.iterdir()} == {"campaign.json", "hi.json", "ur.json"}
    manifest = json.loads((output / "campaign.json").read_text(encoding="utf-8"))
    assert manifest["human_translation_required"] is True
    assert manifest["independent_review_required"] is True
    assert [item["code"] for item in manifest["locales"]] == ["hi", "ur"]
    assert json.loads((output / "ur.json").read_text(encoding="utf-8"))["direction"] == "rtl"
    with pytest.raises(ValueError, match="already exists"):
        create_campaign(output, locales_path=locales, catalog_dir=catalogues)


def test_campaign_check_preserves_translation_work_and_detects_stale_source(tmp_path: Path) -> None:
    locales, catalogues = fixture_catalogue(tmp_path)
    output = tmp_path / "private-campaign"
    create_campaign(output, locales_path=locales, catalog_dir=catalogues)
    packet_path = output / "hi.json"
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    packet["entries"]["hello"]["translation"] = "नमस्ते {name}"
    packet["review"]["translated_by"] = "Private Translator"
    write(packet_path, packet)
    assert validate_campaign(output, locales_path=locales, catalog_dir=catalogues) == {
        "ready_for_human_translation": True,
        "locale_count": 2,
        "message_count": 2,
        "blockers": [],
        "values_redacted": True,
    }

    english_path = catalogues / "en.json"
    english = json.loads(english_path.read_text(encoding="utf-8"))
    english["messages"]["new"] = "New source"
    write(english_path, english)
    stale = validate_campaign(output, locales_path=locales, catalog_dir=catalogues)
    assert stale["ready_for_human_translation"] is False
    assert stale["blockers"] == [
        "campaign.manifest_stale_or_invalid",
        "campaign.packet_invalid.hi",
        "campaign.packet_invalid.ur",
    ]
    assert "Private Translator" not in json.dumps(stale)


def test_repository_campaign_covers_all_planned_languages(tmp_path: Path) -> None:
    output = tmp_path / "all-languages"
    report = create_campaign(output)
    assert report["locale_count"] == 23
    checked = validate_campaign(output)
    assert checked["ready_for_human_translation"] is True
    assert checked["locale_count"] == 23


def test_campaign_output_guard_allows_ignored_paths_but_rejects_runtime_paths() -> None:
    allowed = ROOT / "data" / "translation-campaign" / "fixture"
    assert _safe_output_directory(allowed, ROOT / "config/translations") == allowed.resolve()
    with pytest.raises(ValueError, match="runtime or public"):
        _safe_output_directory(ROOT, ROOT / "config/translations")
    with pytest.raises(ValueError, match="runtime or public"):
        _safe_output_directory(ROOT / "apps/web/public/campaign", ROOT / "config/translations")
    with pytest.raises(ValueError, match="ignored"):
        _safe_output_directory(ROOT / "docs/campaign", ROOT / "config/translations")
