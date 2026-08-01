"""Fail-closed runtime readiness without exposing dependency details."""

from __future__ import annotations

import os
import re
from typing import Any, Mapping

DEPLOYMENT_MODE_ENV = "SIR_SAATHI_DEPLOYMENT_MODE"
RELEASE_COMMIT_ENV = "SIR_SAATHI_RELEASE_COMMIT"
GUIDANCE_MODE = "guidance"
INDEXED_SEARCH_MODE = "indexed-search"
DEPLOYMENT_MODES = {GUIDANCE_MODE, INDEXED_SEARCH_MODE}
RELEASE_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def configured_deployment_mode(environment: Mapping[str, str] | None = None) -> str:
    source = os.environ if environment is None else environment
    mode = source.get(DEPLOYMENT_MODE_ENV, GUIDANCE_MODE).strip()
    if mode not in DEPLOYMENT_MODES:
        raise ValueError(f"{DEPLOYMENT_MODE_ENV} must be guidance or indexed-search")
    return mode


def configured_release_commit(environment: Mapping[str, str] | None = None) -> str:
    source = os.environ if environment is None else environment
    value = source.get(RELEASE_COMMIT_ENV, "development").strip()
    if value != "development" and not RELEASE_COMMIT_PATTERN.fullmatch(value):
        raise ValueError(f"{RELEASE_COMMIT_ENV} must be development or a full lowercase Git commit")
    return value


def _dependency_ready(dependency: Any) -> bool:
    readiness_check = getattr(dependency, "ready", None)
    if not callable(readiness_check):
        return False
    try:
        return readiness_check() is True
    except Exception:
        return False


def runtime_readiness(
    *,
    mode: str,
    abuse_verifier: Any,
    search_backend: Any,
    rate_limiter: Any,
    trusted_proxy_hops: int,
) -> dict[str, object]:
    if mode not in DEPLOYMENT_MODES:
        raise ValueError("mode must be guidance or indexed-search")

    blockers: list[str] = []
    if mode == INDEXED_SEARCH_MODE:
        if abuse_verifier is None:
            blockers.append("indexed_search.turnstile_unavailable")
        if not _dependency_ready(search_backend):
            blockers.append("indexed_search.database_unavailable")
        if not getattr(rate_limiter, "shared", False) or not _dependency_ready(rate_limiter):
            blockers.append("indexed_search.shared_limiter_unavailable")
        if trusted_proxy_hops < 1:
            blockers.append("indexed_search.trusted_proxy_unconfigured")

    return {
        "status": "ready" if not blockers else "not_ready",
        "mode": mode,
        "ready": not blockers,
        "blockers": blockers,
    }
