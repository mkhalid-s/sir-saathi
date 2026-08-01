"""Privacy and abuse-prevention helpers for public API surfaces."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
import ipaddress
import os
import time
from typing import Any, Protocol

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


class RateLimiterUnavailable(RuntimeError):
    """The required shared rate-limit store could not make a decision."""


class RateLimiter(Protocol):
    shared: bool

    def check(self, key: str, *, now: float | None = None) -> RateLimitDecision: ...


@dataclass
class InMemoryRateLimiter:
    """Small fixed-window limiter for the MVP API process."""

    max_requests: int = DEFAULT_RATE_LIMIT_MAX_REQUESTS
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    _buckets: dict[str, list[float]] = field(default_factory=dict)
    shared: bool = field(default=False, init=False)

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


REDIS_URL_ENV = "SIR_SAATHI_REDIS_URL"
TRUSTED_PROXY_HOPS_ENV = "SIR_SAATHI_TRUSTED_PROXY_HOPS"
REDIS_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
local ttl = redis.call('TTL', KEYS[1])
if current == 1 or ttl < 0 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
  ttl = tonumber(ARGV[1])
end
return {current, ttl}
"""


@dataclass
class RedisRateLimiter:
    """Atomic fixed-window limiter shared by every API worker."""

    client: Any
    max_requests: int = DEFAULT_RATE_LIMIT_MAX_REQUESTS
    window_seconds: int = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
    shared: bool = field(default=True, init=False)

    def check(self, key: str, *, now: float | None = None) -> RateLimitDecision:
        del now  # Redis owns the shared window clock/TTL.
        try:
            result = self.client.eval(
                REDIS_RATE_LIMIT_SCRIPT,
                1,
                f"sir-saathi:rate-limit:{key}",
                self.window_seconds,
            )
            if not isinstance(result, (list, tuple)) or len(result) != 2:
                raise ValueError("malformed Redis limiter response")
            current, ttl = int(result[0]), int(result[1])
        except Exception as exc:
            raise RateLimiterUnavailable("shared search rate limiter is unavailable") from exc
        allowed = current <= self.max_requests
        return RateLimitDecision(
            allowed=allowed,
            remaining=max(0, self.max_requests - current),
            retry_after_seconds=0 if allowed else max(1, ttl),
        )

    def ready(self) -> bool:
        """Check the shared limiter without consuming a rate-limit slot."""

        try:
            return self.client.ping() is True
        except Exception:
            return False


def configured_rate_limiter() -> RateLimiter:
    redis_url = os.environ.get(REDIS_URL_ENV)
    if not redis_url:
        return InMemoryRateLimiter(
            max_requests=DEFAULT_PUBLIC_SEARCH_POLICY.rate_limit_max_requests,
            window_seconds=DEFAULT_PUBLIC_SEARCH_POLICY.rate_limit_window_seconds,
        )
    import redis

    return RedisRateLimiter(
        client=redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        ),
        max_requests=DEFAULT_PUBLIC_SEARCH_POLICY.rate_limit_max_requests,
        window_seconds=DEFAULT_PUBLIC_SEARCH_POLICY.rate_limit_window_seconds,
    )


def configured_trusted_proxy_hops() -> int:
    raw_value = os.environ.get(TRUSTED_PROXY_HOPS_ENV, "0")
    try:
        hops = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{TRUSTED_PROXY_HOPS_ENV} must be an integer") from exc
    if hops < 0 or hops > 5:
        raise ValueError(f"{TRUSTED_PROXY_HOPS_ENV} must be between 0 and 5")
    return hops


def resolve_client_ip(*, peer_ip: str | None, forwarded_for: str | None, trusted_proxy_hops: int) -> str | None:
    """Resolve a client IP only across an explicitly configured trusted proxy chain."""

    if trusted_proxy_hops == 0 or not forwarded_for:
        candidate = peer_ip
    else:
        forwarded = [item.strip() for item in forwarded_for.split(",") if item.strip()]
        if len(forwarded) < trusted_proxy_hops:
            return None
        candidate = forwarded[-trusted_proxy_hops]
    try:
        return str(ipaddress.ip_address(candidate)) if candidate else None
    except ValueError:
        return None


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
    abuse_verification_passed: bool,
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
    if state.schedule_provenance.confidence != "official":
        raise ValueError("public search requires official schedule provenance")
    if policy.require_turnstile_for_public_search and not abuse_verification_passed:
        raise ValueError("public search requires abuse-prevention verification")


def assert_rate_limit_allowed(decision: RateLimitDecision) -> None:
    if not decision.allowed:
        raise RateLimitExceeded(f"search rate limit exceeded; retry after {decision.retry_after_seconds} seconds")


def rate_limit_identity(raw_identity: str | None) -> str:
    normalized = " ".join((raw_identity or "unknown-client").strip().split()).casefold()
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return f"client:{digest}"


def search_rate_limit_key(*, client_identity: str | None) -> str:
    """Return one public-search bucket per client, regardless of searched scope.

    A state- or constituency-specific bucket can be bypassed by rotating through
    scopes. The global client bucket keeps the configured burst ceiling meaningful
    across the nationwide search surface.
    """

    return f"search:{rate_limit_identity(client_identity)}"


def verification_rate_limit_key(*, client_identity: str | None) -> str:
    """Keep invalid challenge submissions from flooding the external verifier."""

    return f"verification:{rate_limit_identity(client_identity)}"


def safe_log_query(query: str) -> str:
    normalized = " ".join(query.strip().split())
    return f"len:{len(normalized)}"
