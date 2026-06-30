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
    assert "Schedule source:" in source
    assert "Schedule note:" in source
    assert "Sources last checked:" in source
    assert "Confirm deadlines and eligibility on the official portal" in source
    assert "Indexed public search is not launch-ready" in source
    assert "Guidance only: SIR Saathi does not decide voter eligibility" in source
    assert "replace official ECI, CEO, BLO, or ERO channels" in source


def test_homepage_surfaces_safe_find_name_entry_flow() -> None:
    page_source = (ROOT / "apps/web/src/pages/index.astro").read_text(encoding="utf-8")
    wizard_source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "Find my name safely" in page_source
    assert 'href="#find-name"' in page_source
    assert 'id="find-name"' in wizard_source
    assert "Start with a safe official check" in wizard_source
    assert "does not send these details to SIR Saathi servers" in wizard_source
    assert "call indexed search" in wizard_source
    assert "Open official portal" in wizard_source
    assert "If not found, show missing-name steps" in wizard_source
    assert "updateAnswer('situation', 'missing_name')" in wizard_source
    assert "/api/search" not in wizard_source


def test_web_share_checklist_includes_safety_reminder() -> None:
    source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "shareSafetyText" in source
    assert "Confirm deadlines and eligibility on the official portal" in source
    assert "Do not include EPIC, address, or other private details" in source
    assert "encodeURIComponent(shareText)" in source


def test_web_state_summary_surfaces_source_freshness() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    assert "last_verified" in source
    assert "sourceFreshness" in source
    assert "scheduleProvenance" in source
    assert "last checked" in source


def test_web_surfaces_reviewed_ui_language_readiness() -> None:
    state_source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    wizard_source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "uiLanguageOptionsForState" in state_source
    assert "uiLanguageReadiness" in state_source
    assert "English UI is available now" in state_source
    assert "human review" in state_source
    assert "UI language" in wizard_source
    assert "(planned)" in wizard_source
    assert "UI language status:" in wizard_source


def test_web_copy_does_not_overstate_source_certainty() -> None:
    web_sources = [
        ROOT / "apps/web/src/data/states.ts",
        ROOT / "apps/web/src/components/ActionWizard.tsx",
        ROOT / "apps/web/src/pages/methodology.astro",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in web_sources)
    assert "verified " not in combined.casefold()
    assert "confirm deadlines and eligibility" in combined


def test_public_pages_surface_privacy_launch_rules() -> None:
    privacy_doc = (ROOT / "docs/PRIVACY_AND_ABUSE.md").read_text(encoding="utf-8")
    privacy = (ROOT / "apps/web/src/pages/privacy.astro").read_text(encoding="utf-8")
    data_use = (ROOT / "apps/web/src/pages/data-use.astro").read_text(encoding="utf-8")
    methodology = (ROOT / "apps/web/src/pages/methodology.astro").read_text(encoding="utf-8")
    combined = "\n".join([privacy_doc, privacy, data_use, methodology])
    assert "schedule provenance comes from an official source" in combined
    assert "official schedule provenance" in combined
    assert "Shared checklists must not include EPIC" in privacy_doc
    assert "Shared checklists should not include EPIC, address" in privacy
    assert "Forwarded checklists should stay generic" in data_use
    assert "Keep shared checklists free of EPIC, address" in methodology


def test_web_guidance_escalates_sir_risk_signals() -> None:
    source = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    assert "currentRollFound === 'no'" in source
    assert "baseRollFound === 'yes'" in source
    assert "bloVisited === 'no'" in source
    assert "enumerationFormReceived === 'yes'" in source


def test_web_guidance_covers_backend_supported_situations() -> None:
    schema_source = (ROOT / "services/api/schemas.py").read_text(encoding="utf-8")
    wizard_source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    guidance_source = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    for situation in [
        "existing_voter",
        "new_voter",
        "missing_name",
        "shifted_address",
        "correction",
        "deceased_family",
        "duplicate_entry",
        "portal_failed",
    ]:
        assert f'"{situation}"' in schema_source
        assert f"'{situation}'" in wizard_source
        assert f"'{situation}'" in guidance_source
    assert "form_7" in guidance_source


def test_web_guidance_imports_canonical_forms_catalogue() -> None:
    forms_source = (ROOT / "apps/web/src/data/forms.ts").read_text(encoding="utf-8")
    guidance_source = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    assert "../../../../config/forms/sir-actions.json" in forms_source
    assert "formLabel('form_6')" in guidance_source
    assert "formLabel('form_7')" in guidance_source
    assert "formLabel('form_8')" in guidance_source
    assert "documentsFor('identity', 'address', 'age')" in guidance_source


def test_homepage_surfaces_canonical_forms_reference() -> None:
    page_source = (ROOT / "apps/web/src/pages/index.astro").read_text(encoding="utf-8")
    component_source = (ROOT / "apps/web/src/components/FormsReference.astro").read_text(encoding="utf-8")
    assert "FormsReference" in page_source
    assert "../data/forms" in component_source
    assert "Official form guide" in component_source
    assert "Common document categories" in component_source


def test_homepage_surfaces_privacy_safe_search_availability() -> None:
    page_source = (ROOT / "apps/web/src/pages/index.astro").read_text(encoding="utf-8")
    component_source = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    assert "SearchAvailability" in page_source
    assert "../data/states" in component_source
    assert "Indexed public search is not launch-ready" in component_source
    assert "Schedule provenance:" in component_source
    assert "comes from an official source" in component_source
    assert "state.scheduleProvenance.confidence !== 'official'" in component_source
    assert "rate limits" in component_source
    assert "publicLaunchReady" in component_source


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
