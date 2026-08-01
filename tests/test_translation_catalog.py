import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.translation_catalog import (
    compile_reviewed_packet,
    create_review_packet,
    main,
    render_review_preview,
    translation_readiness,
)


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
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "available"},
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
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "available"},
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
        "review": {
            "status": "reviewed",
            "translated_by": "language translator",
            "reviewed_by": "language reviewer",
            "reviewed_at": "2026-08-01",
        },
        "messages": {"hello": "नमस्कार {name}"},
    })
    report = translation_readiness(locales_path=locales, catalog_dir=catalog_dir)
    assert report["available_locales"] == ["en", "mr"]
    assert report["locales"][1]["blockers"] == []


def test_cli_fails_when_an_available_locale_is_invalid(tmp_path: Path, capsys) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"}
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "draft"},
        "messages": {"hello": "Hello"},
    })
    assert main(["--locales", str(locales), "--catalog-dir", str(catalog_dir), "--fail-on-invalid-available"]) == 1
    assert '"publishable": false' in capsys.readouterr().out


def test_review_packet_is_source_pinned_and_compiles_only_after_human_review(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "planned"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}", "safety": "Check official sources"},
    })

    packet = create_review_packet("mr", locales_path=locales, catalog_dir=catalog_dir)
    assert packet["schema_version"] == 2
    assert packet["direction"] == "ltr"
    assert packet["review"]["status"] == "draft"
    assert packet["entries"]["hello"]["translation"] == ""
    assert packet["entries"]["hello"]["placeholders"] == ["name"]
    assert packet["entries"]["hello"]["section"] == "hello"
    assert packet["entries"]["safety"]["risk"] == "standard"

    packet["review"] = {
        "status": "reviewed",
        "translated_by": "Marathi translator",
        "reviewed_by": "fluent Marathi reviewer",
        "reviewed_at": "2026-08-01",
    }
    packet["entries"]["hello"]["translation"] = "नमस्कार {name}"
    packet["entries"]["safety"]["translation"] = "अधिकृत स्रोत तपासा"
    packet_path = tmp_path / "mr-review.json"
    _write(packet_path, packet)

    catalogue = compile_reviewed_packet(packet_path, locales_path=locales, catalog_dir=catalog_dir)
    assert catalogue["locale"] == "mr"
    assert catalogue["review"]["status"] == "reviewed"
    assert catalogue["messages"]["hello"] == "नमस्कार {name}"


def test_review_packet_rejects_stale_source_and_placeholder_loss(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "planned"},
    ]})
    source = {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}"},
    }
    _write(catalog_dir / "en.json", source)
    packet = create_review_packet("mr", locales_path=locales, catalog_dir=catalog_dir)
    packet["review"] = {
        "status": "reviewed",
        "translated_by": "translator",
        "reviewed_by": "reviewer",
        "reviewed_at": "2026-08-01",
    }
    packet["entries"]["hello"]["translation"] = "नमस्कार"
    packet_path = tmp_path / "mr-review.json"
    _write(packet_path, packet)

    with pytest.raises(ValueError, match="placeholder mismatch"):
        compile_reviewed_packet(packet_path, locales_path=locales, catalog_dir=catalog_dir)

    packet["entries"]["hello"]["translation"] = "नमस्कार {name}"
    _write(packet_path, packet)
    source["messages"]["new"] = "New copy"
    _write(catalog_dir / "en.json", source)
    with pytest.raises(ValueError, match="stale"):
        compile_reviewed_packet(packet_path, locales_path=locales, catalog_dir=catalog_dir)


def test_complete_draft_packet_renders_escaped_rtl_local_review_sheet(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "ur", "label": "Urdu", "direction": "rtl", "status": "planned"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {
            "home.title": "Hello {name}",
            "safety.notice": "Use official sources",
        },
    })
    packet = create_review_packet("ur", locales_path=locales, catalog_dir=catalog_dir)
    packet["entries"]["home.title"]["translation"] = "سلام {name}"
    packet["entries"]["safety.notice"]["translation"] = "<script>صرف سرکاری ذرائع</script>"
    packet_path = tmp_path / "ur-review.json"
    _write(packet_path, packet)

    rendered = render_review_preview(packet_path, locales_path=locales, catalog_dir=catalog_dir)
    assert '<html lang="ur" dir="rtl">' in rendered
    assert "LOCAL DRAFT — NOT REVIEWED, NOT PUBLISHABLE" in rendered
    assert 'meta name="robots" content="noindex, nofollow"' in rendered
    assert "Content-Security-Policy" in rendered
    assert "safety critical" in rendered
    assert "سلام {name}" in rendered
    assert "&lt;script&gt;صرف سرکاری ذرائع&lt;/script&gt;" in rendered
    assert "<script>صرف" not in rendered
    with pytest.raises(ValueError, match="human review status"):
        compile_reviewed_packet(packet_path, locales_path=locales, catalog_dir=catalog_dir)


def test_review_preview_rejects_incomplete_or_placeholder_drift(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "hi", "label": "Hindi", "direction": "ltr", "status": "planned"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello {name}"},
    })
    packet = create_review_packet("hi", locales_path=locales, catalog_dir=catalog_dir)
    packet_path = tmp_path / "hi-review.json"
    _write(packet_path, packet)
    with pytest.raises(ValueError, match="translation is required"):
        render_review_preview(packet_path, locales_path=locales, catalog_dir=catalog_dir)

    packet["entries"]["hello"]["translation"] = "नमस्ते"
    _write(packet_path, packet)
    with pytest.raises(ValueError, match="placeholder mismatch"):
        render_review_preview(packet_path, locales_path=locales, catalog_dir=catalog_dir)


def test_preview_cli_keeps_review_html_out_of_runtime_directories(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "hi", "label": "Hindi", "direction": "ltr", "status": "planned"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello"},
    })
    packet = create_review_packet("hi", locales_path=locales, catalog_dir=catalog_dir)
    packet["entries"]["hello"]["translation"] = "नमस्ते"
    packet_path = tmp_path / "hi-review.json"
    _write(packet_path, packet)

    with pytest.raises(SystemExit):
        main([
            "--locales", str(locales),
            "--catalog-dir", str(catalog_dir),
            "--render-review-preview", str(packet_path),
            "--output", str(catalog_dir / "hi.html"),
        ])
    output = tmp_path / "private-preview" / "hi.html"
    assert main([
        "--locales", str(locales),
        "--catalog-dir", str(catalog_dir),
        "--render-review-preview", str(packet_path),
        "--output", str(output),
    ]) == 0
    assert output.is_file()
    assert "NOT PUBLISHABLE" in output.read_text(encoding="utf-8")


def test_review_packet_requires_distinct_people_and_untampered_risk_metadata(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "planned"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"safety.notice": "Check official sources"},
    })
    packet = create_review_packet("mr", locales_path=locales, catalog_dir=catalog_dir)
    assert packet["entries"]["safety.notice"]["risk"] == "safety_critical"
    packet["entries"]["safety.notice"]["translation"] = "अधिकृत स्रोत तपासा"
    packet["review"] = {
        "status": "reviewed",
        "translated_by": "same person",
        "reviewed_by": "Same Person",
        "reviewed_at": "2026-08-01",
    }
    packet_path = tmp_path / "mr-review.json"
    _write(packet_path, packet)
    with pytest.raises(ValueError, match="different people"):
        compile_reviewed_packet(packet_path, locales_path=locales, catalog_dir=catalog_dir)

    packet["review"]["reviewed_by"] = "independent reviewer"
    packet["entries"]["safety.notice"]["risk"] = "standard"
    _write(packet_path, packet)
    with pytest.raises(ValueError, match="review metadata mismatch"):
        compile_reviewed_packet(packet_path, locales_path=locales, catalog_dir=catalog_dir)


def test_cli_keeps_draft_packets_out_of_runtime_catalogue(tmp_path: Path) -> None:
    locales = tmp_path / "locales.json"
    catalog_dir = tmp_path / "translations"
    _write(locales, {"locales": [
        {"code": "en", "label": "English", "direction": "ltr", "status": "available"},
        {"code": "mr", "label": "Marathi", "direction": "ltr", "status": "planned"},
    ]})
    _write(catalog_dir / "en.json", {
        "schema_version": 1,
        "locale": "en",
        "review": {"status": "source"},
        "messages": {"hello": "Hello"},
    })

    with pytest.raises(SystemExit):
        main([
            "--locales", str(locales),
            "--catalog-dir", str(catalog_dir),
            "--create-review-packet", "mr",
            "--output", str(catalog_dir / "mr.json"),
        ])

    packet_path = tmp_path / "review" / "mr.json"
    assert main([
        "--locales", str(locales),
        "--catalog-dir", str(catalog_dir),
        "--create-review-packet", "mr",
        "--output", str(packet_path),
    ]) == 0
    assert json.loads(packet_path.read_text(encoding="utf-8"))["review"]["status"] == "draft"
