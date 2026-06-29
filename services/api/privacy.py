"""Privacy and abuse-prevention helpers for public API surfaces."""

from __future__ import annotations

from dataclasses import dataclass


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


def safe_log_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    if len(normalized) <= 2:
        return "short-query"
    return f"len:{len(normalized)} prefix:{normalized[:2].casefold()}"
