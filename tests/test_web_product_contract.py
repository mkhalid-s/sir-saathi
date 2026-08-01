import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_web_state_data_imports_canonical_state_configs() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    assert "../../../../config/sir-schedules.json" in source
    for config_path in sorted((ROOT / "config/states").glob("*.json")):
        config = json.loads(config_path.read_text(encoding="utf-8"))
        assert f"../../../../config/states/{config_path.name}" in source
        for date_value in config["sir_schedule"].values():
            if isinstance(date_value, str) and date_value[:4].isdigit():
                assert date_value not in source


def test_public_routes_generate_canonical_locale_alternates_and_sitemap() -> None:
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    sitemap = (ROOT / "apps/web/src/pages/sitemap.xml.ts").read_text(encoding="utf-8")
    robots = (ROOT / "apps/web/src/pages/robots.txt.ts").read_text(encoding="utf-8")
    config = (ROOT / "apps/web/astro.config.mjs").read_text(encoding="utf-8")

    assert 'rel="canonical"' in layout
    assert 'rel="alternate"' in layout
    assert 'hreflang="x-default"' in layout
    assert "availableLocales" in layout
    assert "states.map" in sitemap
    assert "availableLocales.flatMap" in sitemap
    assert "Sitemap:" in robots
    assert "PUBLIC_SITE_URL" in config
    assert "must be an HTTPS origin" in config
    assert "PUBLIC_RELEASE_COMMIT" in config
    assert "full lowercase Git commit" in config
    assert 'name="sir-saathi-release"' in layout


def test_unknown_routes_have_an_accessible_noindex_recovery_page() -> None:
    page = (ROOT / "apps/web/src/pages/404.astro").read_text(encoding="utf-8")
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]

    assert "indexable={false}" in page
    assert 'id="main-content"' in page
    assert 'href="/"' in page
    assert 'href="/#search-availability-title"' in page
    assert 'name="robots" content="noindex, nofollow"' in layout
    assert "all 36 state and union-territory guides" in messages["not_found.copy"]


def test_accessibility_help_is_available_from_every_page_without_collecting_private_data() -> None:
    page = (ROOT / "apps/web/src/pages/accessibility.astro").read_text(encoding="utf-8")
    content = (ROOT / "apps/web/src/components/PolicyContent.astro").read_text(encoding="utf-8")
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]

    assert 'path="/accessibility/"' in page
    assert "localizedPath('/accessibility/', lang)" in layout
    assert "nav.accessibility" in layout
    assert "WCAG 2.2 Level AA" in messages["accessibility.target"]
    assert "not a certification or conformance claim" in messages["accessibility.not_conformance"]
    assert "manual testing" in messages["accessibility.limitation.manual"]
    assert "English is the only reviewed public interface" in messages["accessibility.limitation.languages"]
    assert "issues/new" not in content
    assert "does not yet have an authorized public accessibility-feedback inbox" in messages[
        "accessibility.report_unavailable"
    ]
    assert "must omit your name, EPIC, address" in messages["accessibility.report_privacy"]
    assert "#official-assistance-title" in content
    assert "guidelines.india.gov.in/help/" in content
    assert "www.w3.org/TR/WCAG22/" in content


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
    page_source = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    wizard_source = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    indexed_source = (ROOT / "apps/web/src/components/IndexedSearch.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "home.hero.find" in page_source
    assert "Find my name safely" in messages["home.hero.find"]
    assert 'href="#find-name"' in page_source
    assert 'id="find-name"' in wizard_source
    assert "Start with a safe official check" in messages["find.title"]
    assert "find.state_label" in wizard_source
    assert "updateState" in wizard_source
    assert "setFindSubmitted(false)" in wizard_source
    assert "No name, address, district, constituency, or part number is needed" in messages["find.privacy_notice"]
    assert "sent only when you choose the protected search action" in messages["find.indexed_privacy_notice"]
    assert "official-check-steps" in wizard_source
    assert "Search with the name as it may appear in the roll" in messages["find.step_search"]
    assert "Try common spelling variations" in messages["find.step_spelling"]
    assert "contact BLO or ERO" in messages["find.step_contact"]
    assert "Open official portal" in messages["find.open_official"]
    assert "If not found, show missing-name steps" in messages["find.not_found"]
    assert "find.clear" in wizard_source
    assert "clearFindNameHints" in wizard_source
    assert "setNameQuery('')" in wizard_source
    assert "setAcHint('')" in wizard_source
    assert "setPartHint('')" in wizard_source
    assert "districtHint" not in wizard_source
    assert 'id="find-district"' not in wizard_source
    assert "situation: 'missing_name'" in wizard_source
    assert "currentRollFound: 'no'" in wizard_source
    assert "state.publicLaunchReady" in wizard_source
    private_boundary = wizard_source.index("state.publicLaunchReady && (")
    for private_field in ('id="find-voter-name"', 'id="find-ac"', 'id="find-part"'):
        assert wizard_source.index(private_field) > private_boundary
    assert "fetch('/api/search'" in indexed_source
    assert "turnstile_response: challengeResponse" in indexed_source
    assert "action: 'voter_search'" in indexed_source
    assert "expired-callback" in indexed_source
    assert "window.turnstile.reset" in indexed_source
    assert "challengeContext.current !== searchContext" in indexed_source
    assert "activeRequest.current?.abort()" in indexed_source
    assert "signal: controller.signal" in indexed_source
    assert "submittedContext !== currentSearchContext.current" in indexed_source
    assert "safeSearchResults(payload, stateId, acNumber, partNumber)" in indexed_source
    assert "aria-live=\"polite\"" in indexed_source


def test_find_flow_separates_eci_voter_services_from_state_ceo_portals() -> None:
    forms_source = (ROOT / "apps/web/src/data/forms.ts").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    forms = json.loads((ROOT / "config/forms/sir-actions.json").read_text(encoding="utf-8"))["forms"]
    assert "officialVoterServicesPortal" in forms_source
    assert forms["form_6"]["official_portal"] == "https://voters.eci.gov.in/"
    assert "href={officialVoterServicesPortal}" in wizard
    assert "href={state.officialLink}" in wizard
    assert "find.open_voter_services" in wizard
    assert "find.open_ceo" in wizard
    assert messages["find.open_voter_services"] == "Open ECI voter services"
    assert messages["find.open_ceo"] == "Open {state} CEO portal"


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
    assert "url: scheduleSource.url" in source
    assert "last checked" in source
    assert "timeZone: 'Asia/Kolkata'" in source


def test_state_pages_link_directly_to_schedule_evidence() -> None:
    page = (ROOT / "apps/web/src/components/StateContent.astro").read_text(encoding="utf-8")
    assert "state.scheduleProvenance.url" in page
    assert 'target="_blank"' in page
    assert 'rel="noreferrer"' in page


def test_state_actions_keep_ceo_portals_separate_from_schedule_evidence() -> None:
    source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    for state_id in ["IN-MH", "IN-WB"]:
        config = json.loads((ROOT / f"config/states/{state_id}.json").read_text(encoding="utf-8"))
        schedule_source = next(
            item for item in config["official_sources"]
            if item["label"] == config["schedule_provenance"]["label"]
        )
        assert config["ceo_portal"] != schedule_source["url"]

    assert "officialLink: config.ceo_portal" in source
    assert "officialSource?.url ?? config.ceo_portal" not in source
    assert "url: scheduleSource.url" in source


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
    assert "state.currentPhase !== 'schedule_unverified' && state.currentPhase !== 'schedule_pending'" in wizard
    assert "state?.currentPhase === 'schedule_unverified' || state?.currentPhase === 'schedule_pending'" in guidance
    assert "!scheduleUnavailable && answers.baseRollFound" in guidance
    assert "enumerationActionable && (answers.bloVisited" in guidance
    assert "setAnswers((current) => ({ ...defaultAnswers, situation: current.situation }))" in wizard
    assert "enumerationQuestionsRelevant" in wizard
    assert "baseRollQuestionRelevant" in wizard
    assert "updateSituation" in wizard
    assert "official jurisdiction notice" in messages["guidance.existing.summary_unverified"]


def test_web_guidance_matches_phase_aware_api_outcomes() -> None:
    guidance = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "revisionComplete" in guidance
    assert "guidance.existing.check_final" in guidance
    assert "guidance.existing.current_remedy" in guidance
    assert "guidance.existing.summary_complete" in guidance
    assert "enumerationActionable && answers.enumerationFormReceived" in guidance
    assert "answers.currentRollFound === 'no'" in guidance
    assert "guidance.new.track" in guidance
    assert "deadlineIsoFor" in guidance
    assert "guidance.warning.passed" in guidance
    assert "guidance.warning.close" in guidance
    assert messages["guidance.existing.summary_complete"].startswith("The reviewed revision schedule is complete")


def test_web_guidance_has_an_executable_all_jurisdiction_matrix_gate() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    checker = (ROOT / "scripts/check_web_guidance_matrix.mjs").read_text(encoding="utf-8")
    launch_gate = (ROOT / "scripts/launch_gate.py").read_text(encoding="utf-8")
    assert package["scripts"]["guidance:matrix:check"] == "node scripts/check_web_guidance_matrix.mjs"
    assert "states.length, 36" in checker
    assert "for (const situation of situations)" in checker
    assert "staleEnumeration" in checker
    assert "phaseVariants" in checker
    assert "pre_enumeration" in checker
    assert "enumeration_open" in checker
    assert "final_roll_published" in checker
    assert "schedule_pending" in checker
    assert 'run(["npm", "run", "guidance:matrix:check"])' in launch_gate


def test_web_builds_a_shareable_page_for_every_jurisdiction() -> None:
    page = (ROOT / "apps/web/src/pages/states/[stateId].astro").read_text(encoding="utf-8")
    content = (ROOT / "apps/web/src/components/StateContent.astro").read_text(encoding="utf-8")
    directory = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "getStaticPaths" in page
    assert "states.map" in page
    assert "state.schedule.unverified" in content
    assert "No current SIR schedule has been independently confirmed" in messages["state.schedule.unverified"]
    assert "state.get_checklist" in content
    assert messages["state.get_checklist"] == "Get my action checklist"
    assert "statePath(state)" in directory
    assert "const params = new URLSearchParams(window.location.search)" in wizard
    assert "params.get('state')" in wizard


def test_wizard_deadlines_advance_with_the_current_phase() -> None:
    source = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    assert "state.currentPhase === 'pre_enumeration'" in source
    assert "state.currentPhase === 'pre_draft_publication'" in source
    assert "state.claimsEndIso ?? state.finalRollDateIso" in source
    assert "formatIndiaDate(value, locale)" in source


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
    assert "globallyAvailable" in state_source
    assert "relevantPlanned" in state_source


def test_reviewed_ui_language_is_restored_and_shareable_without_enabling_drafts() -> None:
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    assert "sir-saathi-ui-language" in wizard
    assert "params.get('lang') ?? storedLanguage" in wizard
    assert "hasEnabledCatalogue(preferredLanguage)" in wizard
    assert "window.localStorage.setItem" in wizard
    assert "navigateToLocale(preferredLanguage, true)" in wizard
    assert "localizedPath(suffix, locale)" in wizard
    assert "url.searchParams.delete('lang')" in wizard
    assert "window.history.replaceState" in wizard


def test_reviewed_locale_selection_updates_document_language_and_direction() -> None:
    locales = json.loads((ROOT / "config/locales.json").read_text(encoding="utf-8"))["locales"]
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    states = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    assert {locale["direction"] for locale in locales} == {"ltr", "rtl"}
    assert next(locale for locale in locales if locale["code"] == "ur")["direction"] == "rtl"
    assert "document.documentElement.lang = uiLanguage" in wizard
    assert "document.documentElement.dir = uiLanguageDirection(uiLanguage)" in wizard
    assert "item.status === 'available'" in wizard
    assert "uiLanguageDirection" in states
    assert '<html lang={lang} dir={dir}>' in layout


def test_wizard_controls_and_generated_guidance_are_catalogue_driven() -> None:
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    guidance = (ROOT / "apps/web/src/lib/guidance.ts").read_text(encoding="utf-8")
    api_guidance = (ROOT / "pipeline/sir_saathi_pipeline/guidance.py").read_text(encoding="utf-8")
    indexed = (ROOT / "apps/web/src/components/IndexedSearch.tsx").read_text(encoding="utf-8")
    for key in messages:
        if key.startswith(("guidance.missing.", "guidance.new.", "guidance.shift.", "guidance.correction.",
                           "guidance.deceased.", "guidance.duplicate.", "guidance.portal.",
                           "guidance.existing.", "document.")):
            assert key in guidance or key in api_guidance
        if key.startswith(("find.", "wizard.", "share.")):
            assert f"'{key}'" in wizard
        if key.startswith("search."):
            assert f"'{key}'" in indexed
    assert "guidanceFor(answers, state, uiLanguage)" in wizard


def test_printable_checklist_excludes_private_entry_fields_and_unrelated_content() -> None:
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    styles = (ROOT / "apps/web/src/styles/global.css").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "window.print()" in wizard
    assert "guidance.print_note" in wizard
    assert "print.title" in wizard
    assert messages["guidance.print_note"] == "The printout excludes the name and location fields entered above."
    assert "@media print" in styles
    for private_or_unrelated_surface in (
        ".find-flow",
        ".form-grid",
        ".question-grid",
        ".wizard > .actions",
        ".search-availability",
        ".forms-reference",
    ):
        assert private_or_unrelated_surface in styles


def test_homepage_static_content_and_reviewed_locale_routes_are_catalogue_driven() -> None:
    homepage = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    route = (ROOT / "apps/web/src/pages/[locale]/index.astro").read_text(encoding="utf-8")
    directory = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    forms = (ROOT / "apps/web/src/components/FormsReference.astro").read_text(encoding="utf-8")
    assert "translate(locale" in homepage
    assert '<ActionWizard initialLocale={locale}' in homepage
    assert "availableLocales" in route
    assert "locale.code !== 'en'" in route
    assert "lang={locale.code}" in route
    assert "dir={locale.direction}" in route
    assert "directory.search.not_ready" in directory
    assert "forms.${form.formId}.purpose" in forms
    state_route = (ROOT / "apps/web/src/pages/[locale]/states/[stateId].astro").read_text(encoding="utf-8")
    policy_route = (ROOT / "apps/web/src/pages/[locale]/[policy].astro").read_text(encoding="utf-8")
    state_content = (ROOT / "apps/web/src/components/StateContent.astro").read_text(encoding="utf-8")
    assert "availableLocales" in state_route and "flatMap" in state_route
    assert "availableLocales" in policy_route and "policies.map" in policy_route
    assert "localizedPath(statePath(previousState), locale)" in state_content
    assert "formatIndiaDate(value!, locale)" in state_content
    locale_switcher = (ROOT / "apps/web/src/components/LocaleSwitcher.astro").read_text(encoding="utf-8")
    assert "availableLocales.length > 1" in locale_switcher
    assert "localizedPath(currentPath, option.code)" in locale_switcher
    assert "aria-current" in locale_switcher


def test_public_language_status_page_uses_fail_closed_runtime_catalogues() -> None:
    page = (ROOT / "apps/web/src/pages/languages.astro").read_text(encoding="utf-8")
    component = (ROOT / "apps/web/src/components/LanguageAvailability.astro").read_text(encoding="utf-8")
    localized = (ROOT / "apps/web/src/pages/[locale]/[policy].astro").read_text(encoding="utf-8")
    homepage = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    sitemap = (ROOT / "apps/web/src/pages/sitemap.xml.ts").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "LanguageAvailability" in page
    assert "config/locales.json" in component
    assert "hasEnabledCatalogue(item.code)" in component
    assert "item.status === 'planned' ? 'planned' : 'blocked'" in component
    assert '<table class="language-table">' in component
    assert 'scope="col"' in component and 'scope="row"' in component
    assert 'role="region"' in component and 'tabindex="0"' in component
    assert "path: 'languages'" in localized
    assert "localizedPath('/languages/'" in homepage
    assert "'/languages/'" in sitemap
    assert "human review" in messages["languages.intro"]
    assert "never published automatically" in messages["languages.review_policy"]
    assert "localeRegistry.coverage.source_url" in component
    assert "all 22 languages" in messages["languages.intro"]


def test_jurisdiction_display_names_are_catalogue_driven_across_web_and_api() -> None:
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    directory = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    state_page = (ROOT / "apps/web/src/components/StateContent.astro").read_text(encoding="utf-8")
    api = (ROOT / "services/api/app.py").read_text(encoding="utf-8")
    assert "jurisdictionName(uiLanguage" in wizard
    assert "jurisdictionName(locale" in directory
    assert "jurisdictionName(locale" in state_page
    assert 'f"jurisdiction.{state.state_id}"' in api


def test_web_runtime_revalidates_catalogues_before_generating_locale_routes() -> None:
    i18n = (ROOT / "apps/web/src/lib/i18n.ts").read_text(encoding="utf-8")
    assert "catalogueIsRuntimeReady" in i18n
    assert "catalogue.schema_version !== 1" in i18n
    assert "referenceKeys.length !== candidateKeys.length" in i18n
    assert "placeholders(englishCatalog.messages[key])" in i18n
    assert "catalogue.review?.status === 'reviewed'" in i18n
    assert "catalogue.review.translated_by?.trim()" in i18n
    assert "catalogue.review.reviewed_by?.trim()" in i18n


def test_web_copy_does_not_overstate_source_certainty() -> None:
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    combined = "\n".join(messages.values())
    assert "verified " not in combined.casefold()
    assert "confirm deadlines and eligibility" in combined


def test_public_pages_surface_privacy_launch_rules() -> None:
    privacy_doc = (ROOT / "docs/PRIVACY_AND_ABUSE.md").read_text(encoding="utf-8")
    privacy = (ROOT / "apps/web/src/pages/privacy.astro").read_text(encoding="utf-8")
    data_use = (ROOT / "apps/web/src/pages/data-use.astro").read_text(encoding="utf-8")
    methodology = (ROOT / "apps/web/src/pages/methodology.astro").read_text(encoding="utf-8")
    policy_component = (ROOT / "apps/web/src/components/PolicyContent.astro").read_text(encoding="utf-8")
    translations = (ROOT / "config/translations/en.json").read_text(encoding="utf-8")
    combined = "\n".join([privacy_doc, privacy, data_use, methodology, policy_component, translations])
    assert "schedule provenance comes from an official source" in combined
    assert "official schedule provenance" in combined
    assert "Shared checklists must not include EPIC" in privacy_doc
    assert "Shared checklists should not include EPIC, address" in translations
    assert "Forwarded checklists should stay generic" in translations
    assert "Keep shared checklists free of EPIC, address" in translations


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
    forms = json.loads((ROOT / "config/forms/sir-actions.json").read_text(encoding="utf-8"))["forms"]
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "../../../../config/forms/sir-actions.json" in forms_source
    for form_id in ("form_6", "form_7", "form_8"):
        assert f"form('{form_id}')" in guidance_source
        assert messages[f"forms.{form_id}.label"] == forms[form_id]["label"]
    assert "document.identity" in guidance_source
    assert "document.address" in guidance_source
    assert "document.age" in guidance_source


def test_homepage_surfaces_canonical_forms_reference() -> None:
    page_source = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    component_source = (ROOT / "apps/web/src/components/FormsReference.astro").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "FormsReference" in page_source
    assert "../data/forms" in component_source
    assert "forms.eyebrow" in component_source
    assert messages["forms.eyebrow"] == "Official form guide"
    assert "forms.common_categories" in component_source
    assert messages["forms.common_categories"] == "Common document categories"
    assert "form.officialPortal" in component_source
    assert "forms.open_official" in component_source


def test_every_nationwide_guide_surfaces_governed_official_assistance() -> None:
    home_source = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    state_source = (ROOT / "apps/web/src/components/StateContent.astro").read_text(encoding="utf-8")
    component_source = (ROOT / "apps/web/src/components/OfficialAssistance.astro").read_text(encoding="utf-8")
    data_source = (ROOT / "apps/web/src/data/assistance.ts").read_text(encoding="utf-8")
    config = json.loads((ROOT / "config/official-assistance.json").read_text(encoding="utf-8"))
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "<OfficialAssistance" in home_source
    assert "<OfficialAssistance" in state_source
    assert "stateOfficialLink={state.officialLink}" in state_source
    assert "../../../../config/official-assistance.json" in data_source
    assert {source["url"] for source in config["sources"]} == {
        "https://voters.eci.gov.in/", "https://www.eci.gov.in/contact-us",
        "https://www.eci.gov.in/ceo-contact-details",
    }
    assert {channel["href"] for channel in config["channels"]} == {
        "https://voters.eci.gov.in/", "https://www.eci.gov.in/ceo-contact-details",
        "tel:1950", "mailto:complaints@eci.gov.in"
    }
    assert "<form" not in component_source
    assert "<input" not in component_source
    assert "<textarea" not in component_source
    assert "target={channel.kind === 'web' ? '_blank' : undefined}" in component_source
    assert "rel={channel.kind === 'web' ? 'noreferrer' : undefined}" in component_source
    assert "assistanceSources.map" in component_source
    assert all(channel["source_ids"] for channel in config["channels"])
    for key in (
        "assistance.eyebrow", "assistance.title", "assistance.intro", "assistance.privacy",
        "assistance.source", "assistance.state_portal",
    ):
        assert key in messages
        assert key in component_source


def test_state_guides_render_the_complete_governed_schedule_timeline() -> None:
    state_data = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    state_content = (ROOT / "apps/web/src/components/StateContent.astro").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    fields = {
        "qualifyingDateIso": "state.schedule.qualifying_date",
        "enumerationStartIso": "state.schedule.enumeration_start",
        "enumerationEndIso": "state.schedule.enumeration_end",
        "draftRollDateIso": "state.schedule.draft_roll",
        "claimsStartIso": "state.schedule.claims_start",
        "claimsEndIso": "state.schedule.claims_end",
        "finalRollDateIso": "state.schedule.final_roll",
    }
    for field, message_key in fields.items():
        assert field in state_data
        assert field in state_content
        assert message_key in messages
        assert message_key in state_content
    assert "state.schedule.phase" in state_content
    assert "schedule.phase" in state_data


def test_homepage_surfaces_privacy_safe_search_availability() -> None:
    page_source = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    component_source = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert "SearchAvailability" in page_source
    assert "../data/states" in component_source
    assert "directory.search.not_ready" in component_source
    assert "Indexed public search is not launch-ready" in messages["directory.search.not_ready"]
    assert "directory.provenance" in component_source
    assert messages["directory.provenance"].startswith("Schedule provenance:")
    assert "directory.search.unverified" in component_source
    assert "provenance is confirmed from an official source" in messages["directory.search.unverified"]
    assert "state.scheduleProvenance.confidence !== 'official'" in component_source
    assert "rate limits" in messages["directory.intro"]
    assert "publicLaunchReady" in component_source
    assert "coverage-summary" in component_source
    assert "directory.view_all" in component_source
    assert messages["directory.view_all"].startswith("View status for all")


def test_nationwide_directory_has_progressive_accessible_filtering() -> None:
    component = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    styles = (ROOT / "apps/web/src/styles/global.css").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    assert 'for="jurisdiction-filter"' in component
    assert 'type="search"' in component
    assert 'aria-controls="jurisdiction-list"' in component
    assert 'aria-live="polite"' in component
    assert "data-jurisdiction-row" in component
    assert "row.hidden = !matches" in component
    assert "input.addEventListener('input', update)" in component
    assert ".jurisdiction-row[hidden]" in styles
    assert messages["directory.filter_label"] == "Filter states and union territories"
    assert "{count}" in messages["directory.filter_count"]
    assert "No state or union territory" in messages["directory.filter_empty"]


def test_pwa_manifest_is_installable() -> None:
    manifest = json.loads((ROOT / "apps/web/public/manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifest["display"] == "standalone"
    assert manifest["scope"] == "/"
    assert manifest["id"] == "/"
    assert manifest["lang"] == "en"
    icon_contract = {(icon["sizes"], icon["type"], icon["purpose"]) for icon in manifest["icons"]}
    assert ("192x192", "image/png", "any") in icon_contract
    assert ("512x512", "image/png", "any") in icon_contract
    assert ("512x512", "image/png", "maskable") in icon_contract
    assert ("any", "image/svg+xml", "any") in icon_contract
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    assert 'rel="apple-touch-icon"' in layout


def test_pwa_registers_offline_app_shell_service_worker() -> None:
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    service_worker = (ROOT / "apps/web/public/sw.js").read_text(encoding="utf-8")
    assert "serviceWorker" in layout
    assert "register('/sw.js')" in layout
    assert "APP_SHELL_URLS" in service_worker
    assert "BUILD_ASSET_URLS = []" in service_worker
    assert "PRECACHE_URLS" in service_worker
    assert "'/privacy/'" in service_worker
    assert "'/accessibility/'" in service_worker
    assert "url.pathname.startsWith('/api/')" in service_worker
    assert "response.ok && response.type === 'basic'" in service_worker
    assert "localizedHome" in service_worker
    assert "caches.match(`/${firstSegment}/`)" in service_worker


def test_web_build_finalizes_the_complete_offline_asset_list() -> None:
    package = json.loads((ROOT / "apps/web/package.json").read_text(encoding="utf-8"))
    finalizer = (ROOT / "scripts/finalize_service_worker.mjs").read_text(encoding="utf-8")

    assert "finalize_service_worker.mjs" in package["scripts"]["build"]
    assert "release-manifest.json" in finalizer
    assert "createHash('sha256')" in finalizer
    assert "htmlFiles.length" in finalizer
    assert "built homepage is missing the governed release identity" in finalizer
    assert "filesUnder(dist)" in finalizer
    assert "eligibleExtensions" in finalizer
    assert "index.html" in finalizer
    assert "--check" in finalizer


def test_every_route_announces_when_live_services_are_offline() -> None:
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    status = (ROOT / "apps/web/src/components/ConnectivityStatus.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]

    assert "ConnectivityStatus" in layout
    assert "client:load" in layout
    assert "navigator.onLine" in status
    assert "addEventListener('offline'" in status
    assert 'role="status"' in status
    assert "official links and indexed search" in messages["connectivity.offline"]


def test_pages_have_keyboard_navigation_and_main_landmarks() -> None:
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    styles = (ROOT / "apps/web/src/styles/global.css").read_text(encoding="utf-8")
    assert 'class="skip-link" href="#main-content"' in layout
    assert ":focus-visible" in styles
    for page in (ROOT / "apps/web/src/pages").rglob("*.astro"):
        if page.name == "[stateId].astro" or page.parent == ROOT / "apps/web/src/pages":
            source = page.read_text(encoding="utf-8")
            assert 'id="main-content"' in source or "HomeContent" in source or "PolicyContent" in source or "StateContent" in source or "LanguageAvailability" in source


def test_accessibility_release_policy_covers_manual_and_automated_evidence() -> None:
    policy = (ROOT / "docs/ACCESSIBILITY.md").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "WCAG 2.2 Level AA" in policy
    assert "Passing automated checks is not a conformance claim" in policy
    for requirement in ["NVDA", "VoiceOver", "TalkBack", "400%", "forced-colours", "reduced motion", "Urdu"]:
        assert requirement in policy
    assert "python scripts/check_accessibility.py" in workflow
