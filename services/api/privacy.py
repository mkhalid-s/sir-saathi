"""Privacy and abuse-prevention helpers for public API surfaces."""

from __future__ import annotations

from dataclasses import dataclass

from pipeline.sir_saathi_pipeline.state_registry import StateConfig


@dataclass(frozen=True)
class PublicSearchPolicy:
    require_scope: bool = True
    max_results: int = 20
    allow_bulk_export: bool = False
    reveal_full_epic: bool = False
    reveal_raw_address: bool = False
    require_turnstile_for_public_search: bool = True
    log_full_query: bool = False


DEFAULT_PUBLIC_SEARCH_POLICY = PublicSearchPolicy()


def assert_public_search_policy(policy: PublicSearchPolicy = DEFAULT_PUBLIC_SEARCH_POLICY) -> None:
    if not policy.require_scope:
        raise ValueError("public search must require geographic scope")
    if policy.max_results > 20:
        raise ValueError("public search max_results must be 20 or less")
    if policy.allow_bulk_export:
        raise ValueError("bulk export must be disabled")
    if policy.reveal_full_epic:
        raise ValueError("full EPIC reveal must be disabled")
    if policy.reveal_raw_address:
        raise ValueError("raw address reveal must be disabled")
    if policy.log_full_query:
        raise ValueError("full search query logging must be disabled")


def assert_search_launch_allowed(
    state: StateConfig,
    *,
    turnstile_verified: bool,
    use_sanitized_pilot: bool,
    policy: PublicSearchPolicy = DEFAULT_PUBLIC_SEARCH_POLICY,
) -> None:
    """Fail closed for indexed search unless a safe launch path is explicit."""
    assert_public_search_policy(policy)
    if use_sanitized_pilot:
        return
    if not state.public_launch_ready:
        raise ValueError("indexed search is not enabled for public launch in this state")
    if not state.is_search_enabled:
        raise ValueError("indexed search is not available for this state")
    if policy.require_turnstile_for_public_search and not turnstile_verified:
        raise ValueError("public search requires abuse-prevention verification")


def safe_log_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    if len(normalized) <= 2:
        return "short-query"
    return f"len:{len(normalized)} prefix:{normalized[:2].casefold()}"
