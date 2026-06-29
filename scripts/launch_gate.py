#!/usr/bin/env python3
"""Launch readiness checks for public SIR Saathi slices."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
REQUIRED_FILES = [
    "apps/web/src/pages/privacy.astro",
    "apps/web/src/pages/methodology.astro",
    "apps/web/src/pages/data-use.astro",
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
    required = {"/api/health", "/api/states", "/api/guidance", "/api/search"}
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


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        print("Missing launch files:")
        for path in missing:
            print(f"- {path}")
        return 1
    verify_api_routes()
    verify_deploy_templates()
    run([sys.executable, "scripts/check_sensitive.py"])
    run([sys.executable, "-m", "pytest"])
    run(["npm", "audit", "--workspace", "apps/web"])
    run(["npm", "run", "web:build"])
    print("Launch gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
