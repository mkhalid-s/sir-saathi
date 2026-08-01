from dataclasses import replace

import pytest

from pipeline.sir_saathi_pipeline.state_registry import load_all_states
from services.api.privacy import (
    InMemoryRateLimiter,
    PublicSearchPolicy,
    RateLimitExceeded,
    RateLimiterUnavailable,
    RedisRateLimiter,
    assert_public_search_policy,
    assert_rate_limit_allowed,
    assert_search_launch_allowed,
    rate_limit_identity,
    resolve_client_ip,
    safe_log_query,
    search_rate_limit_key,
    verification_rate_limit_key,
)


def test_default_public_search_policy_is_safe() -> None:
    assert_public_search_policy()


def test_policy_blocks_bulk_export() -> None:
    with pytest.raises(ValueError):
        assert_public_search_policy(PublicSearchPolicy(allow_bulk_export=True))


def test_policy_blocks_unscoped_public_search() -> None:
    with pytest.raises(ValueError):
        assert_public_search_policy(PublicSearchPolicy(require_scope=False))


def test_search_launch_policy_fails_closed_for_non_ready_state() -> None:
    mh = load_all_states()["IN-MH"]
    with pytest.raises(ValueError, match="not enabled for public launch"):
        assert_search_launch_allowed(mh, abuse_verification_passed=False, use_sanitized_pilot=False)


def test_search_launch_policy_allows_sanitized_pilot() -> None:
    mh = load_all_states()["IN-MH"]
    assert_search_launch_allowed(mh, abuse_verification_passed=False, use_sanitized_pilot=True)


def test_public_search_requires_official_schedule_provenance() -> None:
    mh = load_all_states()["IN-MH"]
    reported_provenance = replace(mh.schedule_provenance, confidence="reported")
    launch_ready = replace(
        mh,
        public_launch_ready=True,
        data_capability="validated_indexed_search",
        schedule_provenance=reported_provenance,
    )
    with pytest.raises(ValueError, match="official schedule provenance"):
        assert_search_launch_allowed(launch_ready, abuse_verification_passed=True, use_sanitized_pilot=False)


def test_public_search_allows_official_schedule_provenance_with_server_verification() -> None:
    wb = load_all_states()["IN-WB"]
    launch_ready = replace(wb, public_launch_ready=True, data_capability="validated_indexed_search")
    assert_search_launch_allowed(launch_ready, abuse_verification_passed=True, use_sanitized_pilot=False)


def test_safe_log_query_does_not_store_full_query() -> None:
    summary = safe_log_query("Sample Voter Name")
    assert summary == "len:17"
    assert "sample" not in summary.casefold()


def test_rate_limiter_blocks_repeated_search_bursts() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert_rate_limit_allowed(limiter.check("search:test", now=100.0))
    assert_rate_limit_allowed(limiter.check("search:test", now=101.0))
    with pytest.raises(RateLimitExceeded, match="search rate limit exceeded"):
        assert_rate_limit_allowed(limiter.check("search:test", now=102.0))
    assert_rate_limit_allowed(limiter.check("search:test", now=161.0))


def test_rate_limit_key_does_not_store_raw_client_identity() -> None:
    key = search_rate_limit_key(client_identity="203.0.113.10")
    assert "203.0.113.10" not in key
    assert key.startswith("search:client:")
    assert rate_limit_identity("203.0.113.10") in key


def test_rate_limit_key_cannot_be_evaded_by_rotating_search_scope() -> None:
    first_scope = search_rate_limit_key(client_identity="203.0.113.10")
    second_scope = search_rate_limit_key(client_identity="203.0.113.10")
    assert first_scope == second_scope


def test_verification_flood_limit_is_separate_and_hides_raw_identity() -> None:
    search_key = search_rate_limit_key(client_identity="203.0.113.10")
    verification_key = verification_rate_limit_key(client_identity="203.0.113.10")
    assert verification_key != search_key
    assert verification_key.startswith("verification:client:")
    assert "203.0.113.10" not in verification_key


def test_redis_rate_limiter_uses_one_atomic_expiring_counter_operation() -> None:
    class Client:
        def __init__(self):
            self.calls = []
            self.result = [1, 60]

        def eval(self, *args):
            self.calls.append(args)
            return self.result

    client = Client()
    limiter = RedisRateLimiter(client=client, max_requests=2, window_seconds=60)
    first = limiter.check("search:hashed-scope")
    assert first.allowed is True
    assert first.remaining == 1
    script, key_count, key, window = client.calls[0]
    assert "INCR" in script and "EXPIRE" in script
    assert key_count == 1
    assert key == "sir-saathi:rate-limit:search:hashed-scope"
    assert window == 60

    client.result = [3, 42]
    blocked = limiter.check("search:hashed-scope")
    assert blocked.allowed is False
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds == 42


def test_redis_rate_limiter_fails_closed_when_store_is_unavailable() -> None:
    class Client:
        def eval(self, *_args):
            raise TimeoutError("synthetic timeout")

    with pytest.raises(RateLimiterUnavailable, match="shared search rate limiter is unavailable"):
        RedisRateLimiter(client=Client()).check("search:hashed-scope")


def test_redis_readiness_uses_ping_without_consuming_a_rate_limit_slot() -> None:
    class Client:
        def __init__(self, result=True):
            self.result = result
            self.pings = 0

        def ping(self):
            self.pings += 1
            return self.result

        def eval(self, *_args):
            raise AssertionError("readiness must not consume a limiter slot")

    client = Client()
    assert RedisRateLimiter(client=client).ready() is True
    assert client.pings == 1
    assert RedisRateLimiter(client=Client(False)).ready() is False


def test_client_ip_resolution_trusts_only_configured_proxy_hops() -> None:
    forwarded = "198.51.100.9, 203.0.113.8"
    assert resolve_client_ip(peer_ip="127.0.0.1", forwarded_for=forwarded, trusted_proxy_hops=0) == "127.0.0.1"
    assert resolve_client_ip(peer_ip="127.0.0.1", forwarded_for=forwarded, trusted_proxy_hops=1) == "203.0.113.8"
    assert resolve_client_ip(peer_ip="127.0.0.1", forwarded_for=forwarded, trusted_proxy_hops=2) == "198.51.100.9"
    assert resolve_client_ip(peer_ip="127.0.0.1", forwarded_for="spoofed", trusted_proxy_hops=1) is None
    assert resolve_client_ip(peer_ip="127.0.0.1", forwarded_for="", trusted_proxy_hops=1) == "127.0.0.1"
