import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_state_data_imports_canonical_state_configs() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    for config_path in sorted((ROOT / "config/states").glob("*.json")):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert f"../../../../config/states/{config_path.name}" in source
        for date_value in config["sir_schedule"].values():
            if isinstance(date_value, str) and date_value[:4].isdigit():
                assert date_value not in source


def test_web_wizard_collects_sir_followup_questions() -> None:
    source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    for field in [
        "bloVisited",
        "enumerationFormReceived",
        "enumerationFormSubmitted",
        "currentRollFound",
        "baseRollFound",
    ]:
        assert field in source
    assert "Sources:" in source
    assert "Source freshness:" in source
    assert "Indexed public search is not launch-ready" in source


def test_web_state_summary_surfaces_source_freshness() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    assert "last_verified" in source
    assert "sourceFreshness" in source


def test_web_guidance_escalates_sir_risk_signals() -> None:
    source = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    assert "currentRollFound === 'no'" in source
    assert "baseRollFound === 'yes'" in source
    assert "bloVisited === 'no'" in source
    assert "enumerationFormReceived === 'yes'" in source


def test_pwa_manifest_is_installable() -> None:
    manifest = json.loads((ROOT / "apps/web/public/manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["scope"] == "/"
    assert manifest["icons"]
    assert manifest["icons"][0]["src"] == "/icons/icon.svg"
    assert "maskable" in manifest["icons"][0]["purpose"]


def test_pwa_registers_offline_app_shell_service_worker() -> None:
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    service_worker = (ROOT / "apps/web/public/sw.js").read_text(encoding="utf-8")
    assert "serviceWorker" in layout
    assert "register('/sw.js')" in layout
    assert "APP_SHELL_URLS" in service_worker
    assert "'/privacy/'" in service_worker
    assert "url.pathname.startsWith('/api/')" in service_worker
