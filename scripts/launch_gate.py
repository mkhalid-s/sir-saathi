#!/usr/bin/env python3
"""Launch readiness checks for public SIR Saathi slices."""

from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REQUIRED_FILES = [
    "apps/web/public/icons/icon.svg",
    "apps/web/public/icons/icon-192.png",
    "apps/web/public/icons/icon-512.png",
    "apps/web/public/icons/icon-maskable-512.png",
    "apps/web/public/icons/apple-touch-icon.png",
    "apps/web/public/manifest.webmanifest",
    "apps/web/public/sw.js",
    "apps/web/src/pages/privacy.astro",
    "apps/web/src/pages/methodology.astro",
    "apps/web/src/pages/data-use.astro",
    "apps/web/src/pages/states/[stateId].astro",
    "config/forms/sir-actions.json",
    "docs/PRIVACY_AND_ABUSE.md",
    "docs/LAUNCH_CHECKLIST.md",
    "docs/ACCESSIBILITY.md",
    "services/api/privacy.py",
    "infra/caddy/Caddyfile.example",
    "infra/docker-compose.yml",
    ".github/workflows/source-freshness.yml",
    "requirements.lock",
    "scripts/check_accessibility.py",
    "scripts/check_discoverability.py",
]


def run(command: list[str]) -> None:
    env = dict(os.environ)
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("ASTRO_TELEMETRY_DISABLED", "1")
    subprocess.check_call(command, cwd=ROOT, env=env)


def verify_api_routes() -> None:
    from services.api.app import api_route_paths

    paths = api_route_paths()
    required = {"/api/health", "/api/states", "/api/forms", "/api/guidance", "/api/search"}
    missing = sorted(required - paths)
    if missing:
        raise RuntimeError(f"missing API routes: {missing}")
    if "/search" in paths:
        raise RuntimeError("unprefixed public search route must not be exposed")


def verify_deploy_templates() -> None:
    caddy = (ROOT / "infra/caddy/Caddyfile.example").read_text(encoding="utf-8")
    compose = (ROOT / "infra/docker-compose.yml").read_text(encoding="utf-8")
    systemd = (ROOT / "infra/systemd/sir-saathi-api.service").read_text(encoding="utf-8")
    if "handle /api/*" not in caddy or "reverse_proxy 127.0.0.1:8000" not in caddy:
        raise RuntimeError("Caddy template must proxy /api/* to the local API service")
    if "root * /srv/sir-saathi/web/current" not in caddy or "file_server" not in caddy:
        raise RuntimeError("Caddy must serve the built PWA on the same origin as /api/*")
    if "PWA is served by Cloudflare Pages" in caddy:
        raise RuntimeError("Caddy must not return a placeholder instead of the PWA")
    if 'path /sw.js /manifest.webmanifest' not in caddy or 'Cache-Control "no-cache"' not in caddy:
        raise RuntimeError("service-worker control files must remain revalidatable")
    required_headers = {
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Cross-Origin-Resource-Policy",
        "Content-Security-Policy",
    }
    missing_headers = sorted(header for header in required_headers if header not in caddy)
    if missing_headers:
        raise RuntimeError(f"Caddy template is missing browser security headers: {missing_headers}")
    csp_requirements = {
        "default-src 'none'",
        "frame-ancestors 'none'",
        "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com",
        "connect-src 'self' https://challenges.cloudflare.com",
        "frame-src https://challenges.cloudflare.com",
    }
    if any(directive not in caddy for directive in csp_requirements):
        raise RuntimeError("browser CSP must stay deny-by-default and Turnstile-compatible")
    if "POSTGRES_HOST_AUTH_METHOD" in compose or "127.0.0.1:5432:5432" not in compose:
        raise RuntimeError("local compose must not expose unauthenticated Postgres")
    if "redis:8-alpine" not in compose or "127.0.0.1:6379:6379" not in compose:
        raise RuntimeError("local compose must provide a loopback-only shared rate-limit store")
    if "services.api.app:create_configured_app --factory" not in systemd:
        raise RuntimeError("API service must use the environment-configured application factory")
    lock_lines = [
        line.strip()
        for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not lock_lines or any("==" not in line for line in lock_lines):
        raise RuntimeError("production Python dependencies must use exact versions in requirements.lock")


def verify_abuse_protection() -> None:
    privacy = (ROOT / "services/api/privacy.py").read_text(encoding="utf-8")
    app = (ROOT / "services/api/app.py").read_text(encoding="utf-8")
    schemas = (ROOT / "services/api/schemas.py").read_text(encoding="utf-8")
    verifier = (ROOT / "services/api/abuse_verification.py").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "InMemoryRateLimiter" not in privacy or "search_rate_limit_key" not in privacy:
        raise RuntimeError("public search must define rate limiting helpers")
    if "DEFAULT_SEARCH_RATE_LIMITER" not in app or "request.client.host" not in app:
        raise RuntimeError("public search route must apply client-scoped rate limiting")
    if "turnstile_verified" in schemas or "turnstile_response" not in schemas:
        raise RuntimeError("public API must accept an opaque token, never a client verification claim")
    if "siteverify" not in verifier or "expected_hostname" not in verifier or "expected_action" not in verifier:
        raise RuntimeError("Turnstile must be verified server-side with hostname and action checks")
    if "configured_abuse_verifier" not in app or "abuse_verification_passed=verification_passed" not in app:
        raise RuntimeError("public search route must use only server-owned abuse verification")
    backend = (ROOT / "services/api/search_backend.py").read_text(encoding="utf-8")
    schema = (ROOT / "db/schema.sql").read_text(encoding="utf-8")
    if "public_search_scopes" not in backend or "scope.enabled = TRUE" not in backend:
        raise RuntimeError("database search must use the reviewed exact-scope allowlist")
    if "public_search_scopes" not in schema or "reviewed_by TEXT NOT NULL" not in schema:
        raise RuntimeError("public search scope activation must retain reviewer metadata")
    if "search_backend=search_backend" not in app:
        raise RuntimeError("public route must pass only its configured server-side search backend")
    if "RedisRateLimiter" not in privacy or "REDIS_RATE_LIMIT_SCRIPT" not in privacy or "redis>=" not in requirements:
        raise RuntimeError("real public search must have an atomic shared Redis limiter")
    if "not rate_limiter.shared" not in app or "RateLimiterUnavailable" not in app:
        raise RuntimeError("real public search must fail closed without the shared limiter")
    if "resolve_client_ip" not in app or "TRUSTED_PROXY_HOPS_ENV" not in privacy:
        raise RuntimeError("client identity must use explicit trusted-proxy configuration")


def verify_source_freshness() -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo
    from pipeline.sir_saathi_pipeline.source_freshness import build_freshness_report

    web = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    search_availability = (ROOT / "apps/web/src/components/SearchAvailability.astro").read_text(encoding="utf-8")
    api = (ROOT / "services/api/app.py").read_text(encoding="utf-8")
    schedule_catalogue = json.loads((ROOT / "config/sir-schedules.json").read_text(encoding="utf-8"))
    freshness_workflow = (ROOT / ".github/workflows/source-freshness.yml").read_text(encoding="utf-8")
    if "schedule:" not in freshness_workflow or "cron:" not in freshness_workflow:
        raise RuntimeError("official source freshness must run on an unattended schedule")
    if "workflow_dispatch:" not in freshness_workflow:
        raise RuntimeError("official source freshness must support an operator-triggered run")
    if "source_freshness" not in freshness_workflow or "--fail-on-stale" not in freshness_workflow:
        raise RuntimeError("scheduled source freshness must fail closed on stale evidence")
    if "upload-artifact@v4" not in freshness_workflow or "if: always()" not in freshness_workflow:
        raise RuntimeError("scheduled source freshness must retain its safe report on failure")
    if "guidance.sources_checked" not in web or "Sources last checked:" not in messages["guidance.sources_checked"] or "last_verified" not in api:
        raise RuntimeError("official source freshness must be visible in web and API surfaces")
    if "guidance.schedule_source" not in web or "guidance.schedule_note" not in web or "schedule_provenance" not in api:
        raise RuntimeError("schedule provenance must be visible in web and API surfaces")
    if "verified " in web.casefold():
        raise RuntimeError("web source freshness copy must not imply official verification")
    if "directory.provenance" not in search_availability or "directory.search.unverified" not in search_availability:
        raise RuntimeError("search availability must show official schedule provenance requirement")
    schedule_source = schedule_catalogue.get("source", {})
    if schedule_source.get("source_type") != "official_portal" or not schedule_source.get("last_verified"):
        raise RuntimeError("shared nationwide schedule must retain official provenance and freshness")
    scheduled_ids = [
        state_id
        for group in schedule_catalogue.get("schedule_groups", [])
        for state_id in group.get("state_ids", [])
    ]
    phase_three_ids = [
        state_id
        for group in schedule_catalogue.get("schedule_groups", [])
        if group.get("phase") == "Phase III"
        for state_id in group.get("state_ids", [])
    ]
    if len(phase_three_ids) != 19 or len(set(phase_three_ids)) != 19:
        raise RuntimeError("Phase III schedule catalogue must cover exactly 19 unique jurisdictions")
    if len(scheduled_ids) != len(set(scheduled_ids)):
        raise RuntimeError("reviewed schedule catalogue must not duplicate jurisdictions")
    if len(scheduled_ids) != 35:
        raise RuntimeError("reviewed shared schedule catalogue must cover 35 exact jurisdictions")
    for group in schedule_catalogue.get("schedule_groups", []):
        group_source = group.get("source", schedule_source)
        if group_source.get("source_type") != "official_portal" or not group_source.get("last_verified"):
            raise RuntimeError("every reviewed schedule group must have fresh official provenance")
    if "sir-schedules.json" not in (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8"):
        raise RuntimeError("web state catalogue must consume shared reviewed schedules")
    for path in sorted((ROOT / "config/states").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        provenance = data.get("schedule_provenance", {})
        if provenance.get("confidence") not in {"official", "reported"}:
            raise RuntimeError(f"missing schedule provenance confidence in {path.name}")
        source_by_label = {
            source.get("label"): source
            for source in data.get("official_sources", [])
        }
        matching_source = source_by_label.get(provenance.get("label"))
        if matching_source is None:
            raise RuntimeError(f"schedule provenance source must be listed in {path.name}")
        if matching_source.get("source_type") != provenance.get("source_type"):
            raise RuntimeError(f"schedule provenance source_type must match listed source in {path.name}")
        if provenance.get("confidence") == "official" and provenance.get("source_type") != "official_portal":
            raise RuntimeError(f"official schedule provenance must use official_portal in {path.name}")
        if not provenance.get("notes"):
            raise RuntimeError(f"schedule provenance must include notes in {path.name}")
        for source in data.get("official_sources", []):
            if not source.get("last_verified"):
                raise RuntimeError(f"missing source freshness in {path.name}: {source.get('label', 'unknown')}")
    report = build_freshness_report(today=datetime.now(ZoneInfo("Asia/Kolkata")).date())
    if not report["ready"]:
        stale_labels = ", ".join(
            f"{finding['state_id']}:{finding['source_label']}" for finding in report["stale"]
        )
        raise RuntimeError(f"official source metadata is stale: {stale_labels}")


def verify_pwa_installability() -> None:
    import struct

    manifest = json.loads((ROOT / "apps/web/public/manifest.webmanifest").read_text(encoding="utf-8"))
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    service_worker = (ROOT / "apps/web/public/sw.js").read_text(encoding="utf-8")
    if manifest.get("display") != "standalone" or manifest.get("scope") != "/":
        raise RuntimeError("PWA manifest must be standalone and scoped to the app root")
    icons = manifest.get("icons", [])
    icon_contract = {(icon.get("sizes"), icon.get("type"), icon.get("purpose")) for icon in icons}
    required_icons = {
        ("192x192", "image/png", "any"),
        ("512x512", "image/png", "any"),
        ("512x512", "image/png", "maskable"),
        ("any", "image/svg+xml", "any"),
    }
    if not required_icons.issubset(icon_contract):
        raise RuntimeError("PWA manifest must include interoperable any and maskable icon variants")
    for name, expected_size in {
        "icon-192.png": 192,
        "icon-512.png": 512,
        "icon-maskable-512.png": 512,
        "apple-touch-icon.png": 180,
    }.items():
        data = (ROOT / "apps/web/public/icons" / name).read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
            raise RuntimeError(f"{name} must be a valid PNG")
        width, height = struct.unpack(">II", data[16:24])
        if (width, height) != (expected_size, expected_size):
            raise RuntimeError(f"{name} must be {expected_size}x{expected_size}")
    if 'rel="apple-touch-icon"' not in layout:
        raise RuntimeError("PWA layout must expose the mobile touch icon")
    if "navigator.serviceWorker.register('/sw.js')" not in layout:
        raise RuntimeError("PWA layout must register the service worker")
    if "APP_SHELL_URLS" not in service_worker or "url.pathname.startsWith('/api/')" not in service_worker:
        raise RuntimeError("service worker must cache the app shell and avoid API caching")
    if "BUILD_ASSET_URLS = []" not in service_worker or "PRECACHE_URLS" not in service_worker:
        raise RuntimeError("service worker source must accept the complete generated offline asset list")
    if "response.ok && response.type === 'basic'" not in service_worker:
        raise RuntimeError("service worker must not cache failed or opaque responses")
    if "localizedHome" not in service_worker or "firstSegment" not in service_worker:
        raise RuntimeError("offline navigation must preserve a previously cached reviewed locale")
    if 'class="skip-link" href="#main-content"' not in layout:
        raise RuntimeError("web layout must provide keyboard skip navigation")


def verify_ui_language_readiness() -> None:
    from pipeline.sir_saathi_pipeline.translation_catalog import translation_readiness

    states_source = (ROOT / "apps/web/src/data/states.ts").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    i18n = (ROOT / "apps/web/src/lib/i18n.ts").read_text(encoding="utf-8")
    localized_home = ROOT / "apps/web/src/pages/[locale]/index.astro"
    localized_state = ROOT / "apps/web/src/pages/[locale]/states/[stateId].astro"
    localized_policy = ROOT / "apps/web/src/pages/[locale]/[policy].astro"
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    api = (ROOT / "services/api/app.py").read_text(encoding="utf-8")
    api_schema = (ROOT / "services/api/schemas.py").read_text(encoding="utf-8")
    api_guidance = (ROOT / "pipeline/sir_saathi_pipeline/guidance.py").read_text(encoding="utf-8")
    runtime_translations = (ROOT / "pipeline/sir_saathi_pipeline/translations.py").read_text(encoding="utf-8")
    locale_switcher = (ROOT / "apps/web/src/components/LocaleSwitcher.astro").read_text(encoding="utf-8")
    if "wizard.language_planned" not in wizard or "English UI is available now" not in messages["wizard.language_available"]:
        raise RuntimeError("web must expose explicit UI language readiness")
    if "human review" not in messages["wizard.language_planned"]:
        raise RuntimeError("planned non-English UI translations must require human review")
    if "wizard.ui_language" not in wizard or "wizard.planned_suffix" not in wizard:
        raise RuntimeError("wizard must show available and planned UI language status")
    if "import.meta.glob" not in i18n or "hasEnabledCatalogue" not in i18n or "translate(uiLanguage" not in wizard:
        raise RuntimeError("reviewed translation catalogues must drive rendered wizard copy")
    if "catalogueIsRuntimeReady" not in i18n or "referenceKeys.length !== candidateKeys.length" not in i18n:
        raise RuntimeError("web runtime must independently reject incomplete available catalogues")
    if not all(path.is_file() for path in (localized_home, localized_state, localized_policy)):
        raise RuntimeError("reviewed locales must generate home, state, and policy routes")
    if "localizedPath" not in i18n or "navigateToLocale" not in wizard:
        raise RuntimeError("reviewed locale navigation must preserve locale-prefixed public routes")
    if "resolve_locale" not in api or "locale_fallback" not in api or '"locale"' not in api_schema:
        raise RuntimeError("API locale negotiation must expose explicit reviewed fallback metadata")
    if "translate_message" not in api_guidance or "translation_readiness" not in runtime_translations:
        raise RuntimeError("API guidance must use the same fail-closed reviewed catalogue as the PWA")
    jurisdiction_keys = {key for key in messages if key.startswith("jurisdiction.")}
    if len(jurisdiction_keys) != 36:
        raise RuntimeError("all 36 jurisdiction display names must be governed translation keys")
    if "localizedPath(currentPath, option.code)" not in locale_switcher or "aria-current" not in locale_switcher:
        raise RuntimeError("reviewed locale switcher must preserve the current route and expose current language")
    report = translation_readiness()
    invalid_available = [
        item["locale"]
        for item in report["locales"]
        if item["registry_status"] == "available" and not item["publishable"]
    ]
    if invalid_available:
        raise RuntimeError(f"available locales have incomplete or unreviewed catalogues: {', '.join(invalid_available)}")


def verify_safe_share_copy() -> None:
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    if "shareSafetyText" not in wizard or "encodeURIComponent(shareText)" not in wizard:
        raise RuntimeError("wizard must use explicit safe checklist share text")
    if "Confirm deadlines and eligibility on the official portal" not in messages["safety.confirm_official"]:
        raise RuntimeError("shared checklist must ask users to confirm official deadlines")
    if "Do not include EPIC, address" not in messages["safety.no_private_share"]:
        raise RuntimeError("shared checklist must warn against forwarding private voter details")


def verify_guidance_boundary_copy() -> None:
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    if "safety.guidance_boundary" not in wizard or "Guidance only: SIR Saathi does not decide voter eligibility" not in messages["safety.guidance_boundary"]:
        raise RuntimeError("wizard must say guidance is not an eligibility decision")
    if "replace official ECI, CEO, BLO, or ERO channels" not in messages["safety.guidance_boundary"]:
        raise RuntimeError("wizard must direct final decisions to official channels")


def verify_safe_find_name_flow() -> None:
    homepage = (ROOT / "apps/web/src/components/HomeContent.astro").read_text(encoding="utf-8")
    wizard = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    indexed = (ROOT / "apps/web/src/components/IndexedSearch.tsx").read_text(encoding="utf-8")
    messages = json.loads((ROOT / "config/translations/en.json").read_text(encoding="utf-8"))["messages"]
    if "home.hero.find" not in homepage or "Find my name safely" not in messages["home.hero.find"] or 'href="#find-name"' not in homepage:
        raise RuntimeError("homepage must expose a clear safe find-name entry point")
    if 'id="find-name"' not in wizard or "Start with a safe official check" not in messages["find.title"]:
        raise RuntimeError("wizard must contain the safe find-name flow")
    if "find.state_label" not in wizard or "updateState" not in wizard:
        raise RuntimeError("find-name flow must ask for state before official search steps")
    if "setFindSubmitted(false)" not in wizard:
        raise RuntimeError("find-name flow must hide stale official-check results when state changes")
    if "does not send these details to SIR Saathi servers" not in messages["find.privacy_notice"]:
        raise RuntimeError("find-name flow must explain local-only fallback behavior")
    if "official-check-steps" not in wizard:
        raise RuntimeError("find-name flow must show official-check steps before missing-name guidance")
    for key, expected in [
        ("find.step_search", "Search with the name as it may appear in the roll"),
        ("find.step_spelling", "Try common spelling variations"),
        ("find.step_contact", "contact BLO or ERO"),
    ]:
        if key not in wizard or expected not in messages[key]:
            raise RuntimeError("find-name flow must show official-check steps before missing-name guidance")
    if "call indexed search" not in messages["find.privacy_notice"]:
        raise RuntimeError("official fallback must explain that it does not call indexed search")
    if "state.publicLaunchReady" not in wizard or "fetch('/api/search'" not in indexed:
        raise RuntimeError("indexed-search client must render only for launch-ready jurisdictions")
    for expected in ["turnstile_response: challengeResponse", "action: 'voter_search'", "expired-callback", "window.turnstile.reset"]:
        if expected not in indexed:
            raise RuntimeError("indexed-search client must use a fresh action-bound Turnstile response")
    if "find.not_found" not in wizard or "situation: 'missing_name'" not in wizard or "currentRollFound: 'no'" not in wizard:
        raise RuntimeError("find-name flow must hand off to missing-name guidance with current-roll-not-found status")
    if "find.clear" not in wizard or "clearFindNameHints" not in wizard:
        raise RuntimeError("find-name flow must let users clear local search hints")
    for setter in ["setNameQuery('')", "setDistrictHint('')", "setAcHint('')", "setPartHint('')"]:
        if setter not in wizard:
            raise RuntimeError("find-name flow must clear all local search hint fields")


def verify_public_privacy_pages() -> None:
    privacy_doc = (ROOT / "docs/PRIVACY_AND_ABUSE.md").read_text(encoding="utf-8")
    privacy = (ROOT / "apps/web/src/pages/privacy.astro").read_text(encoding="utf-8")
    data_use = (ROOT / "apps/web/src/pages/data-use.astro").read_text(encoding="utf-8")
    methodology = (ROOT / "apps/web/src/pages/methodology.astro").read_text(encoding="utf-8")
    policy = (ROOT / "apps/web/src/components/PolicyContent.astro").read_text(encoding="utf-8")
    translations = (ROOT / "config/translations/en.json").read_text(encoding="utf-8")
    combined = "\n".join([privacy_doc, privacy, data_use, methodology, policy, translations])
    if "schedule provenance comes from an official source" not in combined:
        raise RuntimeError("public pages must explain official schedule provenance requirement")
    if "official schedule provenance before launch" not in privacy_doc:
        raise RuntimeError("privacy policy must require official schedule provenance before launch")
    if "Shared checklists must not include EPIC" not in privacy_doc:
        raise RuntimeError("privacy policy must cover safe checklist forwarding")
    if "Shared checklists should not include EPIC, address" not in translations:
        raise RuntimeError("privacy page must warn against forwarding private voter details")
    if "Forwarded checklists should stay generic" not in translations:
        raise RuntimeError("data-use page must cover safe checklist forwarding")
    if "Keep shared checklists free of EPIC, address" not in translations:
        raise RuntimeError("methodology page must cover safe checklist forwarding")


def verify_forms_catalogue() -> None:
    from services.api.app import forms_payload

    payload = forms_payload()
    form_ids = {form["form_id"] for form in payload["forms"]}
    required = {"enumeration_form", "form_6", "form_7", "form_8"}
    if required - form_ids:
        raise RuntimeError("forms catalogue must expose all MVP SIR forms")


def verify_state_schedule_api() -> None:
    from services.api.app import list_states_payload

    states = list_states_payload()
    if len(states) != 36:
        raise RuntimeError("state API must expose all 36 Indian states and union territories")
    for state in states:
        schedule = state.get("sir_schedule")
        if not isinstance(schedule, dict):
            raise RuntimeError("state payload must expose structured SIR schedule metadata")
        if "status" not in schedule or "current_phase" not in schedule or "final_roll_date" not in schedule:
            raise RuntimeError("state schedule payload must include status, current_phase, and final_roll_date")
        if "ceo_portal" not in state:
            raise RuntimeError("state payload must include CEO portal")
        provenance = state.get("schedule_provenance")
        if not isinstance(provenance, dict) or provenance.get("confidence") not in {"official", "reported", "unverified"}:
            raise RuntimeError("state payload must expose explicit schedule provenance confidence")


def verify_ingestion_pipeline_contract() -> None:
    ingestion = (ROOT / "pipeline/sir_saathi_pipeline/ingestion.py").read_text(encoding="utf-8")
    ingest_cli = (ROOT / "pipeline/sir_saathi_pipeline/ingest_roll.py").read_text(encoding="utf-8")
    sources = (ROOT / "pipeline/sir_saathi_pipeline/sources.py").read_text(encoding="utf-8")
    db_loader = (ROOT / "pipeline/sir_saathi_pipeline/db_loader.py").read_text(encoding="utf-8")
    schema = (ROOT / "db/schema.sql").read_text(encoding="utf-8")
    seed_states = (ROOT / "pipeline/sir_saathi_pipeline/seed_states.py").read_text(encoding="utf-8")
    local_search = (ROOT / "pipeline/sir_saathi_pipeline/local_search.py").read_text(encoding="utf-8")
    readiness = (ROOT / "pipeline/sir_saathi_pipeline/readiness_report.py").read_text(encoding="utf-8")
    workflow = (ROOT / "pipeline/sir_saathi_pipeline/operator_workflow.py").read_text(encoding="utf-8")
    public_scope = (ROOT / "pipeline/sir_saathi_pipeline/public_search_scope.py").read_text(encoding="utf-8")
    parser_registry = (ROOT / "pipeline/sir_saathi_pipeline/parsers/registry.py").read_text(encoding="utf-8")
    matching = (ROOT / "pipeline/sir_saathi_pipeline/cross_year_matching.py").read_text(encoding="utf-8")
    docs = (ROOT / "docs/API_AND_DB.md").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    if "build_ingestion_batch" not in ingestion or "ParsedRollInput" not in ingestion:
        raise RuntimeError("pipeline must expose a DB-ready ingestion batch builder")
    if "parsed record count mismatch" not in ingestion:
        raise RuntimeError("ingestion pipeline must validate parser counts before DB staging")
    if "epic_fingerprint" not in ingestion or "epic_hash" not in ingestion or "epic_last4" not in ingestion:
        raise RuntimeError("ingestion pipeline must hash EPIC values before DB staging")
    if "connect(" in ingestion or "psycopg" in ingestion:
        raise RuntimeError("initial ingestion mapper must not connect to the database")
    if '"district":' not in ingestion and "district=district" not in ingestion:
        raise RuntimeError("ingestion must preserve reviewed district relationships")
    if "INSERT INTO districts" not in db_loader or "source_updated_at" not in schema:
        raise RuntimeError("database loading must preserve geographic source provenance")
    if "geography_version" not in schema or 'startswith("reviewed:")' not in matching:
        raise RuntimeError("historical/current matching must use versioned, reviewed geography scopes")
    if "status: str = \"proposed\"" not in matching or "human review" not in matching:
        raise RuntimeError("cross-year matching must remain proposal-only and human-reviewed")
    if "voter_record_match_candidates" not in schema or "reviewed_at IS NOT NULL" not in schema:
        raise RuntimeError("cross-year match persistence must require review metadata for decisions")
    if "local-only staging mapper" not in docs:
        raise RuntimeError("API/DB docs must document local-only ingestion boundaries")
    if "parsed_roll_from_pdf" not in ingest_cli or "build_ingestion_batch" not in ingest_cli:
        raise RuntimeError("ingest CLI must reuse registered parsers and the DB-ready staging mapper")
    if "validate_parser_scope" not in ingest_cli or "ingestion_ready=False" not in parser_registry:
        raise RuntimeError("parser routing must reject unvalidated parser families before ingestion")
    if "--dry-run" not in ingest_cli or "SIR_SAATHI_EPIC_HASH_SALT" not in ingest_cli:
        raise RuntimeError("ingest CLI must require explicit dry-run mode and an EPIC hash salt")
    if "save_results" in ingest_cli or "connect(" in ingest_cli or "psycopg" in ingest_cli:
        raise RuntimeError("ingest CLI must not write exports or connect to the database")
    if "Local PDF ingestion can be validated with a dry run" not in docs:
        raise RuntimeError("API/DB docs must document the local PDF dry-run command")
    if "validate_source_manifest" not in sources or "reviewed" not in sources:
        raise RuntimeError("source manifests must require reviewed metadata before ingestion")
    if "local_path must stay under ignored data/ or samples/" not in sources:
        raise RuntimeError("source manifests must keep local PDFs under ignored paths")
    if "validate_parser_scope" not in sources or "require_ready=True" not in sources:
        raise RuntimeError("source manifests must pin an ingestion-ready parser with valid scope")
    if "checksum must be sha256:<64 lowercase hex>" not in sources or "compute_sha256" not in sources:
        raise RuntimeError("source manifests must require sha256 checksums")
    if "--verify-file" not in sources or "local file checksum does not match source manifest" not in sources:
        raise RuntimeError("source manifest validation must be able to verify local files")
    if "draft_source_manifest_entry" not in sources or '"reviewed": False' not in sources:
        raise RuntimeError("source manifest drafting must never auto-mark entries as reviewed")
    if "valid_for_ingestion" not in sources or "ready_for_review" not in sources:
        raise RuntimeError("source manifest drafting must distinguish review from ingestion readiness")
    if "write_draft_source_manifest_entry" not in sources or "source_id already exists in manifest" not in sources:
        raise RuntimeError("source manifest drafting must support safe local manifest writes without duplicates")
    if "--output-manifest" not in sources or "manifest path must stay under ignored data/ or samples/" not in sources:
        raise RuntimeError("source manifest write path must stay under ignored local roots")
    if "source_manifest_review_report" not in sources or "ready_for_human_review" not in sources:
        raise RuntimeError("source manifests must expose a local human-review readiness report")
    if "--review" not in sources or "valid_for_ingestion" not in sources:
        raise RuntimeError("source manifest review command must distinguish review readiness from ingestion readiness")
    if "Before parsing a local PDF, validate a reviewed source manifest entry" not in docs:
        raise RuntimeError("API/DB docs must document source manifest validation")
    if "Operators can draft a manifest entry" not in docs or "reviewed: false" not in docs or "--output-manifest" not in docs:
        raise RuntimeError("API/DB docs must document source manifest drafting")
    if "Operators can generate a local review report" not in docs or "ready_for_human_review" not in docs:
        raise RuntimeError("API/DB docs must document source manifest review reporting")
    if "--expected-checksum" not in ingest_cli or "checksum does not match expected source manifest checksum" not in ingest_cli:
        raise RuntimeError("ingest CLI must fail closed on manifest checksum mismatches")
    if "--load" not in ingest_cli or "SIR_SAATHI_DATABASE_URL" not in ingest_cli:
        raise RuntimeError("ingest CLI must require an explicit local load mode and database URL")
    if "load_ingestion_batch" not in db_loader or "load_batch_to_database" not in db_loader:
        raise RuntimeError("pipeline must expose a local Postgres batch loader")
    if "require_state_exists" not in db_loader or "transaction()" not in db_loader:
        raise RuntimeError("Postgres loader must require a canonical state row and use a transaction")
    if "ON CONFLICT" not in db_loader or "DO UPDATE" not in db_loader:
        raise RuntimeError("Postgres loader must use idempotent upserts")
    if "psycopg.connect" not in db_loader or "psycopg[binary]" not in requirements:
        raise RuntimeError("Postgres loader must use psycopg v3 and declare the dependency")
    if "seed_states" not in seed_states or "load_all_states" not in seed_states:
        raise RuntimeError("pipeline must expose local canonical state seeding")
    if "INSERT INTO states" not in seed_states or "ON CONFLICT (state_id) DO UPDATE" not in seed_states:
        raise RuntimeError("state seed command must use idempotent state upserts")
    if "public_launch_ready" not in seed_states or "SIR_SAATHI_DATABASE_URL" not in seed_states:
        raise RuntimeError("state seed command must mirror launch flags from config and require DB URL")
    if "Before loading rolls, seed canonical state rows" not in docs:
        raise RuntimeError("API/DB docs must document local state seeding before roll loads")
    if "public_launch_ready" in db_loader + ingest_cli + local_search or "/api/search" in db_loader + ingest_cli + local_search + readiness + workflow:
        raise RuntimeError("local ingestion loaders must not change public search launch behavior")
    if "After a dry run passes" not in docs or "does not enable public search" not in docs:
        raise RuntimeError("API/DB docs must document local load boundaries")
    if "LocalSearchRequest" not in local_search or "validate_local_search" not in local_search:
        raise RuntimeError("pipeline must expose local loaded-roll search validation")
    if "similarity(vr.name_normalized" not in local_search or "JOIN assembly_constituencies" not in local_search:
        raise RuntimeError("local search validation must use scoped pg_trgm name similarity")
    if "safe_for_public" not in local_search or "query_summary" not in local_search:
        raise RuntimeError("local search validation must report safe local-only metadata")
    if "MAX_LOCAL_SEARCH_LIMIT" not in local_search or "include_epic_last4" not in local_search:
        raise RuntimeError("local search validation must cap results and hide EPIC last4 by default")
    if "Local loaded-roll search can be validated" not in docs:
        raise RuntimeError("API/DB docs must document the local loaded-roll search command")
    if "ReadinessRequest" not in readiness or "validate_readiness" not in readiness:
        raise RuntimeError("pipeline must expose a local readiness report")
    if "ready_for_public" not in readiness or "safe_for_public" not in readiness:
        raise RuntimeError("readiness report must distinguish local readiness from public safety")
    if "readiness_blockers" not in readiness or "state.public_launch_ready" not in readiness:
        raise RuntimeError("readiness report must include config and data blockers")
    if "voter_records" not in readiness or "quality_issue_rate" not in readiness:
        raise RuntimeError("readiness report must summarize scoped loaded data quality")
    if "Loaded data readiness can be checked" not in docs:
        raise RuntimeError("API/DB docs must document the local readiness report command")
    if "WorkflowRequest" not in workflow or "build_workflow" not in workflow:
        raise RuntimeError("pipeline must expose a local operator workflow planner")
    for expected_step in ["seed_states", "validate_source_manifest", "dry_run_pdf", "load_pdf", "validate_search", "readiness_report"]:
        if expected_step not in workflow:
            raise RuntimeError("operator workflow must include the full local onboarding sequence")
    if "SIR_SAATHI_TEST_NAME" not in workflow or "does not print the raw query" not in docs:
        raise RuntimeError("operator workflow must keep local search names out of reports")
    if "--verify-file" not in workflow or "--expected-checksum" not in workflow:
        raise RuntimeError("operator workflow must verify manifest checksums before parse/load")
    if "Operators can generate the full local onboarding workflow" not in docs:
        raise RuntimeError("API/DB docs must document the local operator workflow")
    if "public_search_scope_events" not in schema or "readiness_snapshot JSONB NOT NULL" not in schema:
        raise RuntimeError("public search scope changes must retain append-only readiness evidence")
    if "public_search_scope_events_append_only" not in schema or "BEFORE UPDATE OR DELETE" not in schema:
        raise RuntimeError("public search scope audit events must reject mutation at the database layer")
    if "SET TRANSACTION ISOLATION LEVEL SERIALIZABLE" not in public_scope or "authorization_sql" not in public_scope:
        raise RuntimeError("scope readiness evidence and authorization changes must be atomic")
    if "if not apply" not in public_scope or "action == \"enable\" and report[\"blockers\"]" not in public_scope:
        raise RuntimeError("public search scope promotion must be dry-run-first and fail closed")
    if "action not in {\"enable\", \"disable\"}" not in public_scope:
        raise RuntimeError("public search scope authorization must support explicit revocation")
    if "Exact public-search scopes are managed" not in docs:
        raise RuntimeError("API/DB docs must document audited exact-scope authorization")


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        print("Missing launch files:")
        for path in missing:
            print(f"- {path}")
        return 1
    verify_api_routes()
    verify_deploy_templates()
    verify_abuse_protection()
    verify_source_freshness()
    verify_pwa_installability()
    verify_ui_language_readiness()
    verify_safe_share_copy()
    verify_guidance_boundary_copy()
    verify_safe_find_name_flow()
    verify_public_privacy_pages()
    verify_forms_catalogue()
    verify_state_schedule_api()
    verify_ingestion_pipeline_contract()
    run([sys.executable, "scripts/check_sensitive.py"])
    run([sys.executable, "-m", "pytest"])
    run(["npm", "audit", "--workspace", "apps/web"])
    run(["npm", "run", "pwa:icons:check"])
    run(["npm", "run", "web:build"])
    run(["npm", "run", "pwa:offline:check"])
    run([sys.executable, "scripts/check_accessibility.py"])
    run([sys.executable, "scripts/check_discoverability.py"])
    print("Launch gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
