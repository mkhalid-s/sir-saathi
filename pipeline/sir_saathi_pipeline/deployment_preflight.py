"""Secret-safe, read-only production configuration preflight."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
from typing import Mapping
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_SITE_URL_ENV = "PUBLIC_SITE_URL"
WEB_URL_ENV = "WEB_URL"
PUBLIC_TURNSTILE_SITE_KEY_ENV = "PUBLIC_TURNSTILE_SITE_KEY"
PUBLIC_RELEASE_COMMIT_ENV = "PUBLIC_RELEASE_COMMIT"
API_RELEASE_COMMIT_ENV = "SIR_SAATHI_RELEASE_COMMIT"
DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"
REDIS_URL_ENV = "SIR_SAATHI_REDIS_URL"
TURNSTILE_SECRET_ENV = "SIR_SAATHI_TURNSTILE_SECRET"
TURNSTILE_HOSTNAME_ENV = "SIR_SAATHI_TURNSTILE_HOSTNAME"
TRUSTED_PROXY_HOPS_ENV = "SIR_SAATHI_TRUSTED_PROXY_HOPS"
BACKUP_DIR_ENV = "SIR_SAATHI_BACKUP_DIR"
AGE_RECIPIENT_ENV = "SIR_SAATHI_AGE_RECIPIENT"
DEPLOYMENT_MODE_ENV = "SIR_SAATHI_DEPLOYMENT_MODE"
RESERVED_PUBLIC_SUFFIXES = (".example", ".invalid", ".localhost", ".test")
RELEASE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _public_origin(value: str) -> tuple[str | None, str | None]:
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        return None, None
    try:
        ipaddress.ip_address(hostname)
        is_ip = True
    except ValueError:
        is_ip = False
    if (
        parsed.scheme != "https"
        or not hostname
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or hostname == "localhost"
        or hostname.endswith(RESERVED_PUBLIC_SUFFIXES)
        or is_ip
    ):
        return None, None
    port_suffix = f":{port}" if port else ""
    return f"https://{hostname}{port_suffix}", hostname


def _service_url(value: str, schemes: set[str]) -> bool:
    try:
        parsed = urlparse(value)
        hostname = parsed.hostname or ""
        parsed.port
    except ValueError:
        return False
    return parsed.scheme in schemes and bool(hostname) and not hostname.endswith(RESERVED_PUBLIC_SUFFIXES)


def preflight(mode: str, environment: Mapping[str, str]) -> dict[str, object]:
    if mode not in {"guidance", "indexed-search"}:
        raise ValueError("mode must be guidance or indexed-search")
    blockers: list[str] = []
    site_value = environment.get(PUBLIC_SITE_URL_ENV, "")
    web_value = environment.get(WEB_URL_ENV, "")
    site_origin, site_hostname = _public_origin(site_value)
    web_origin, _web_hostname = _public_origin(web_value)
    if not site_origin:
        blockers.append(f"{PUBLIC_SITE_URL_ENV} must be a non-reserved HTTPS origin")
    if not web_origin:
        blockers.append(f"{WEB_URL_ENV} must be a non-reserved HTTPS origin")
    if site_origin and web_origin and site_origin != web_origin:
        blockers.append(f"{WEB_URL_ENV} must match {PUBLIC_SITE_URL_ENV}")
    runtime_mode = environment.get(DEPLOYMENT_MODE_ENV, "guidance").strip()
    if runtime_mode != mode:
        blockers.append(f"{DEPLOYMENT_MODE_ENV} must match the selected deployment mode")
    public_commit = environment.get(PUBLIC_RELEASE_COMMIT_ENV, "").strip()
    api_commit = environment.get(API_RELEASE_COMMIT_ENV, "").strip()
    if not RELEASE_COMMIT_PATTERN.fullmatch(public_commit):
        blockers.append(f"{PUBLIC_RELEASE_COMMIT_ENV} must be the full lowercase Git commit")
    if not RELEASE_COMMIT_PATTERN.fullmatch(api_commit):
        blockers.append(f"{API_RELEASE_COMMIT_ENV} must be the full lowercase Git commit")
    if public_commit and api_commit and public_commit != api_commit:
        blockers.append("PWA and API release commits must match")

    if mode == "indexed-search":
        required = [
            DEPLOYMENT_MODE_ENV,
            PUBLIC_TURNSTILE_SITE_KEY_ENV,
            DATABASE_URL_ENV,
            REDIS_URL_ENV,
            TURNSTILE_SECRET_ENV,
            TURNSTILE_HOSTNAME_ENV,
            TRUSTED_PROXY_HOPS_ENV,
            BACKUP_DIR_ENV,
            AGE_RECIPIENT_ENV,
        ]
        for name in required:
            if not environment.get(name, "").strip():
                blockers.append(f"{name} is required for indexed-search deployment")

        public_turnstile_value = environment.get(PUBLIC_TURNSTILE_SITE_KEY_ENV, "").strip()
        server_turnstile_value = environment.get(TURNSTILE_SECRET_ENV, "").strip()
        if public_turnstile_value and server_turnstile_value and public_turnstile_value == server_turnstile_value:
            blockers.append("Turnstile public and server-owned values must be different")
        configured_hostname = environment.get(TURNSTILE_HOSTNAME_ENV, "").strip().casefold()
        if site_hostname and configured_hostname and configured_hostname != site_hostname.casefold():
            blockers.append(f"{TURNSTILE_HOSTNAME_ENV} must match the public site hostname")
        if environment.get(DATABASE_URL_ENV) and not _service_url(
            environment[DATABASE_URL_ENV], {"postgres", "postgresql"}
        ):
            blockers.append(f"{DATABASE_URL_ENV} must be a PostgreSQL connection URL")
        if environment.get(REDIS_URL_ENV) and not _service_url(
            environment[REDIS_URL_ENV], {"redis", "rediss"}
        ):
            blockers.append(f"{REDIS_URL_ENV} must be a Redis connection URL")
        try:
            proxy_hops = int(environment.get(TRUSTED_PROXY_HOPS_ENV, ""))
        except ValueError:
            proxy_hops = 0
        if proxy_hops < 1 or proxy_hops > 5:
            blockers.append(f"{TRUSTED_PROXY_HOPS_ENV} must be between 1 and 5 in production")

        raw_backup_dir = environment.get(BACKUP_DIR_ENV, "")
        backup_dir = Path(raw_backup_dir) if raw_backup_dir else None
        if backup_dir:
            resolved = backup_dir.resolve()
            if (
                not backup_dir.is_absolute()
                or backup_dir.is_symlink()
                or not resolved.is_dir()
                or resolved == ROOT
                or ROOT in resolved.parents
                or resolved.stat().st_mode & 0o077
            ):
                blockers.append(f"{BACKUP_DIR_ENV} must be an existing private directory outside the repository")
        recipient = environment.get(AGE_RECIPIENT_ENV, "").strip()
        if recipient and any(character.isspace() for character in recipient):
            blockers.append(f"{AGE_RECIPIENT_ENV} must contain one age recipient")

    return {
        "mode": mode,
        "ready": not blockers,
        "blockers": blockers,
        "checked_fields": 5 if mode == "guidance" else 13,
        "values_redacted": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check deployment configuration without printing values.")
    parser.add_argument("--mode", choices=["guidance", "indexed-search"], default="guidance")
    args = parser.parse_args(argv)
    report = preflight(args.mode, os.environ)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
