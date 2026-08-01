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
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    for field in [
        "bloVisited",
        "enumerationFormReceived",
        "enumerationFormSubmitted",
        "currentRollFound",
        "baseRollFound",
    ]:
        assert field in source
    assert "guidance.sources" in source
    assert "guidance.schedule_source" in source
    assert "guidance.schedule_note" in source
    assert "guidance.sources_checked" in source
    assert "Confirm deadlines and eligibility on the official portal" in messages["safety.confirm_official"]
    assert "Indexed public search is not launch-ready" in messages["safety.search_unavailable"]
    assert "Guidance only: SIR Saathi does not decide voter eligibility" in messages["safety.guidance_boundary"]
    assert "replace official ECI, CEO, BLO, or ERO channels" in messages["safety.guidance_boundary"]
    assert "translate(uiLanguage" in source


def test_homepage_surfaces_safe_find_name_entry_flow() -> None:
    page_source = (ROOT / "apps/web/src/pages/index.astro").read_text(encoding="utf-8")
    wizard_source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    indexed_source = (ROOT / "apps/web/src/components/IndexedSearch.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "Find my name safely" in page_source
    assert 'href="#find-name"' in page_source
    assert 'id="find-name"' in wizard_source
    assert "Start with a safe official check" in messages["find.title"]
    assert "find.state_label" in wizard_source
    assert "updateState" in wizard_source
    assert "setFindSubmitted(false)" in wizard_source
    assert "does not send these details to SIR Saathi servers" in messages["find.privacy_notice"]
    assert "call indexed search" in messages["find.privacy_notice"]
    assert "official-check-steps" in wizard_source
    assert "Search with the name as it may appear in the roll" in messages["find.step_search"]
    assert "Try common spelling variations" in messages["find.step_spelling"]
    assert "contact BLO or ERO" in messages["find.step_contact"]
    assert "Open official portal" in messages["find.open_official"]
    assert "If not found, show missing-name steps" in messages["find.not_found"]
    assert "find.clear" in wizard_source
    assert "clearFindNameHints" in wizard_source
    assert "setNameQuery('')" in wizard_source
    assert "setDistrictHint('')" in wizard_source
    assert "setAcHint('')" in wizard_source
    assert "setPartHint('')" in wizard_source
    assert "situation: 'missing_name'" in wizard_source
    assert "currentRollFound: 'no'" in wizard_source
    assert "state.publicLaunchReady" in wizard_source
    assert "fetch('/api/search'" in indexed_source
    assert "turnstile_response: challengeResponse" in indexed_source
    assert "action: 'voter_search'" in indexed_source
    assert "expired-callback" in indexed_source
    assert "window.turnstile.reset" in indexed_source
    assert "aria-live=\"polite\"" in indexed_source


def test_web_share_checklist_includes_safety_reminder() -> None:
    source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "shareSafetyText" in source
    assert "Confirm deadlines and eligibility on the official portal" in messages["safety.confirm_official"]
    assert "Do not include EPIC, address" in messages["safety.no_private_share"]
    assert "encodeURIComponent(shareText)" in source


def test_web_state_summary_surfaces_source_freshness() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    assert "last_verified" in source
    assert "sourceFreshness" in source
    assert "scheduleProvenance" in source
    assert "last checked" in source


def test_web_state_summary_derives_current_schedule_phase() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    assert "currentPhaseForSchedule" in source
    assert "Asia/Kolkata" in source
    for phase in [
        "pre_enumeration",
        "enumeration_open",
        "pre_draft_publication",
        "claims_and_objections_open",
        "claims_disposal",
        "final_roll_published",
    ]:
        assert phase in source


def test_web_state_registry_uses_all_nationwide_jurisdictions() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    catalogue = json.loads((ROOT / "config/jurisdictions.json").read_text(encoding="utf-8"))
    assert "jurisdictionCatalogue.jurisdictions" in source
    assert len(catalogue["jurisdictions"]) == 36
    assert len({item["state_id"] for item in catalogue["jurisdictions"]}) == 36


def test_web_preserves_canonical_language_codes() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "languageCodes: string[]" in source
    assert "code: locale.code" in source
    assert "state.languageCodes" in wizard
    assert "config/locales.json" in source
    assert "localeByCode" in source


def test_web_hides_schedule_specific_questions_when_schedule_is_unknown() -> None:
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    guidance = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "state.currentPhase !== 'schedule_unverified'" in wizard
    assert "scheduleUnverified" in guidance
    assert "official jurisdiction notice" in messages["guidance.existing.summary_unverified"]


def test_web_builds_a_shareable_page_for_every_jurisdiction() -> None:
    page = (ROOT / "apps/web/src/pages/states/[stateId].astro").read_text(encoding="utf-8")
    directory = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "getStaticPaths" in page
    assert "states.map" in page
    assert "No current SIR schedule has been independently confirmed" in page
    assert "Get my action checklist" in page
    assert "statePath(state)" in directory
    assert "new URLSearchParams(window.location.search).get('state')" in wizard


def test_wizard_deadlines_advance_with_the_current_phase() -> None:
    source = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    assert "state.currentPhase === 'pre_enumeration'" in source
    assert "state.currentPhase === 'pre_draft_publication'" in source
    assert "return state.claimsEnd ?? state.finalRollDate" in source


def test_web_surfaces_reviewed_ui_language_readiness() -> None:
    state_source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    wizard_source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "uiLanguageOptionsForState" in state_source
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "wizard.language_planned" in wizard_source
    assert "English UI is available now" in messages["wizard.language_available"]
    assert "human review" in messages["wizard.language_planned"]
    assert "wizard.ui_language" in wizard_source
    assert "wizard.planned_suffix" in wizard_source
    assert "guidance.language_status" in wizard_source
    i18n_source = (ROOT / "apps/web/src/lib/i18n.ts").read_text(encoding="utf-8")
    assert "import.meta.glob" in i18n_source
    assert "locale.status === 'available'" in i18n_source


def test_wizard_controls_and_generated_guidance_are_catalogue_driven() -> None:
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    guidance = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    indexed = (ROOT / "apps/web/src/components/IndexedSearch.tsx").read_text(encoding="utf-8")
    for key in messages:
        if key.startswith(("guidance.missing.", "guidance.new.", "guidance.shift.", "guidance.correction.",
                           "guidance.deceased.", "guidance.duplicate.", "guidance.portal.",
                           "guidance.existing.", "document.")):
            assert f"'{key}'" in guidance
        if key.startswith(("find.", "wizard.", "share.")):
            assert f"'{key}'" in wizard
        if key.startswith("search."):
            assert f"'{key}'" in indexed
    assert "guidanceFor(answers, state, uiLanguage)" in wizard


def test_web_copy_does_not_overstate_source_certainty() -> None:
    web_sources = [
        ROOT / "apps/web/src/data/states.ts",
        ROOT / "apps/web/src/components/ActionWizard.tsx",
        ROOT / "apps/web/src/pages/methodology.astro",
        ROOT / "config/translations/en.json",
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
    assert "document.identity" in guidance_source
    assert "document.address" in guidance_source
    assert "document.age" in guidance_source


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
    assert "current schedule is verified from an official source" in component_source
    assert "state.scheduleProvenance.confidence !== 'official'" in component_source
    assert "rate limits" in component_source
    assert "publicLaunchReady" in component_source
    assert "coverage-summary" in component_source
    assert "View status for all" in component_source


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
    assert "response.ok && response.type === 'basic'" in service_worker


def test_pages_have_keyboard_navigation_and_main_landmarks() -> None:
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    styles = (ROOT / "apps/web/src/styles/global.css").read_text(encoding="utf-8")
    assert 'class="skip-link" href="#main-content"' in layout
    assert ":focus-visible" in styles
    for page in (ROOT / "apps/web/src/pages").rglob("*.astro"):
        if page.name == "[stateId].astro" or page.parent == ROOT / "apps/web/src/pages":
            assert 'id="main-content"' in page.read_text(encoding="utf-8")
