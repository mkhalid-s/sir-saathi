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
    "apps/web/public/manifest.webmanifest",
    "apps/web/public/sw.js",
    "apps/web/src/pages/privacy.astro",
    "apps/web/src/pages/methodology.astro",
    "apps/web/src/pages/data-use.astro",
    "config/forms/sir-actions.json",
    "docs/PRIVACY_AND_ABUSE.md",
    "docs/LAUNCH_CHECKLIST.md",
    "services/api/privacy.py",
    "infra/caddy/Caddyfile.example",
    "infra/docker-compose.yml",
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
    if "handle /api/*" not in caddy or "reverse_proxy 127.0.0.1:8000" not in caddy:
        raise RuntimeError("Caddy template must proxy /api/* to the local API service")
    if "POSTGRES_HOST_AUTH_METHOD" in compose or "127.0.0.1:5432:5432" not in compose:
        raise RuntimeError("local compose must not expose unauthenticated Postgres")


def verify_abuse_protection() -> None:
    privacy = (ROOT / "services/api/privacy.py").read_text(encoding="utf-8")
    app = (ROOT / "services/api/app.py").read_text(encoding="utf-8")
    if "InMemoryRateLimiter" not in privacy or "search_rate_limit_key" not in privacy:
        raise RuntimeError("public search must define rate limiting helpers")
    if "DEFAULT_SEARCH_RATE_LIMITER" not in app or "request.client.host" not in app:
        raise RuntimeError("public search route must apply client-scoped rate limiting")


def verify_source_freshness() -> None:
    web = (ROOT / "apps/web/src/components/ActionWizard.tsx").read_text(encoding="utf-8")
    api = (ROOT / "services/api/app.py").read_text(encoding="utf-8")
    if "Source freshness:" not in web or "last_verified" not in api:
        raise RuntimeError("official source freshness must be visible in web and API surfaces")
    for path in sorted((ROOT / "config/states").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for source in data.get("official_sources", []):
            if not source.get("last_verified"):
                raise RuntimeError(f"missing source freshness in {path.name}: {source.get('label', 'unknown')}")


def verify_pwa_installability() -> None:
    manifest = json.loads((ROOT / "apps/web/public/manifest.webmanifest").read_text(encoding="utf-8"))
    layout = (ROOT / "apps/web/src/layouts/BaseLayout.astro").read_text(encoding="utf-8")
    service_worker = (ROOT / "apps/web/public/sw.js").read_text(encoding="utf-8")
    if manifest.get("display") != "standalone" or manifest.get("scope") != "/":
        raise RuntimeError("PWA manifest must be standalone and scoped to the app root")
    if not manifest.get("icons"):
        raise RuntimeError("PWA manifest must include an icon")
    if "navigator.serviceWorker.register('/sw.js')" not in layout:
        raise RuntimeError("PWA layout must register the service worker")
    if "APP_SHELL_URLS" not in service_worker or "url.pathname.startsWith('/api/')" not in service_worker:
        raise RuntimeError("service worker must cache the app shell and avoid API caching")


def verify_forms_catalogue() -> None:
    from services.api.app import forms_payload

    payload = forms_payload()
    form_ids = {form["form_id"] for form in payload["forms"]}
    required = {"enumeration_form", "form_6", "form_7", "form_8"}
    if required - form_ids:
        raise RuntimeError("forms catalogue must expose all MVP SIR forms")


def verify_state_schedule_api() -> None:
    from services.api.app import list_states_payload

    for state in list_states_payload():
        schedule = state.get("sir_schedule")
        if not isinstance(schedule, dict):
            raise RuntimeError("state payload must expose structured SIR schedule metadata")
        if "status" not in schedule or "final_roll_date" not in schedule:
            raise RuntimeError("state schedule payload must include status and final_roll_date")
        if "ceo_portal" not in state:
            raise RuntimeError("state payload must include CEO portal")


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
    verify_forms_catalogue()
    verify_state_schedule_api()
    run([sys.executable, "scripts/check_sensitive.py"])
    run([sys.executable, "-m", "pytest"])
    run(["npm", "audit", "--workspace", "apps/web"])
    run(["npm", "run", "web:build"])
    print("Launch gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
