"""Privacy and abuse-prevention helpers for public API surfaces."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

from pipeline.sir_saathi_pipeline.state_registry import StateConfig


DEFAULT_RATE_LIMIT_MAX_REQUESTS = 30
DEFAULT_RATE_LIMIT_WINDOW_SECONDS = 60


@dataclass(frozen=True)
class PublicSearchPolicy:
    require_scope: bool = True
    max_results: int = 20
    allow_bulk_export: bool = False
    reveal_full_epic: bool = False
    reveal_raw_address: bool = False
    require_turnstile_for_public_search: bool = True
    log_full_query: bool = False
    rate_limit_max_requests: int = DEFAULT_RATE_LIMIT_MAX_REQUESTS
    rate_limit_window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after_seconds: int = 0


class RateLimitExceeded(ValueError):
    """Search rate limit was exceeded."""


@dataclass
class InMemoryRateLimiter:
    """Small fixed-window limiter for the MVP API process."""

    max_requests: int = DEFAULT_RATE_LIMIT_MAX_REQUESTS
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    _buckets: dict[str, list[float]] = field(default_factory=dict)

    def check(self, key: str, *, now: float | None = None) -> RateLimitDecision:
        current_time = time.monotonic() if now is None else now
        window_start = current_time - self.window_seconds
        bucket = [timestamp for timestamp in self._buckets.get(key, []) if timestamp > window_start]
        if len(bucket) >= self.max_requests:
            oldest = min(bucket)
            retry_after = max(1, int(round((oldest + self.window_seconds) - current_time)))
            self._buckets[key] = bucket
            return RateLimitDecision(allowed=False, remaining=0, retry_after_seconds=retry_after)
        bucket.append(current_time)
        self._buckets[key] = bucket
        return RateLimitDecision(allowed=True, remaining=self.max_requests - len(bucket))


DEFAULT_PUBLIC_SEARCH_POLICY = PublicSearchPolicy()
DEFAULT_SEARCH_RATE_LIMITER = InMemoryRateLimiter(
    max_requests=DEFAULT_PUBLIC_SEARCH_POLICY.rate_limit_max_requests,
    window_seconds=DEFAULT_PUBLIC_SEARCH_POLICY.rate_limit_window_seconds,
)


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
    if policy.rate_limit_max_requests < 1 or policy.rate_limit_max_requests > 120:
        raise ValueError("search rate limit must be between 1 and 120 requests")
    if policy.rate_limit_window_seconds < 10 or policy.rate_limit_window_seconds > 3600:
        raise ValueError("search rate limit window must be between 10 and 3600 seconds")


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


def assert_rate_limit_allowed(decision: RateLimitDecision) -> None:
    if not decision.allowed:
        raise RateLimitExceeded(f"search rate limit exceeded; retry after {decision.retry_after_seconds} seconds")


def rate_limit_identity(raw_identity: str | None) -> str:
    normalized = " ".join((raw_identity or "unknown-client").strip().split()).casefold()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"client:{digest}"


def search_rate_limit_key(*, client_identity: str | None, state_id: str, ac_number: int) -> str:
    return f"search:{rate_limit_identity(client_identity)}:state:{state_id}:ac:{ac_number}"


def safe_log_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    if len(normalized) <= 2:
        return "short-query"
    return f"len:{len(normalized)} prefix:{normalized[:2].casefold()}"
