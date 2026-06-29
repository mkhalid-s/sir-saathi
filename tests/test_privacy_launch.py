from dataclasses import replace

import pytest

from pipeline.sir_saathi_pipeline.state_registry import load_all_states
from services.api.privacy import (
    InMemoryRateLimiter,
    PublicSearchPolicy,
    RateLimitExceeded,
    assert_public_search_policy,
    assert_rate_limit_allowed,
    assert_search_launch_allowed,
    rate_limit_identity,
    safe_log_query,
    search_rate_limit_key,
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
        assert_search_launch_allowed(mh, turnstile_verified=False, use_sanitized_pilot=False)


def test_search_launch_policy_allows_sanitized_pilot() -> None:
    mh = load_all_states()["IN-MH"]
    assert_search_launch_allowed(mh, turnstile_verified=False, use_sanitized_pilot=True)


def test_public_search_requires_official_schedule_provenance() -> None:
    mh = load_all_states()["IN-MH"]
    launch_ready = replace(mh, public_launch_ready=True, data_capability="validated_indexed_search")
    with pytest.raises(ValueError, match="official schedule provenance"):
        assert_search_launch_allowed(launch_ready, turnstile_verified=True, use_sanitized_pilot=False)


def test_public_search_allows_official_schedule_provenance_with_turnstile() -> None:
    wb = load_all_states()["IN-WB"]
    launch_ready = replace(wb, public_launch_ready=True, data_capability="validated_indexed_search")
    assert_search_launch_allowed(launch_ready, turnstile_verified=True, use_sanitized_pilot=False)


def test_safe_log_query_does_not_store_full_query() -> None:
    assert safe_log_query("Sample Voter Name") == "len:17 prefix:sa"


def test_rate_limiter_blocks_repeated_search_bursts() -> None:
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60)
    assert_rate_limit_allowed(limiter.check("search:test", now=100.0))
    assert_rate_limit_allowed(limiter.check("search:test", now=101.0))
    with pytest.raises(RateLimitExceeded, match="search rate limit exceeded"):
        assert_rate_limit_allowed(limiter.check("search:test", now=102.0))
    assert_rate_limit_allowed(limiter.check("search:test", now=161.0))


def test_rate_limit_key_does_not_store_raw_client_identity() -> None:
    key = search_rate_limit_key(client_identity="203.0.113.10", state_id="IN-MH", ac_number=172)
    assert "203.0.113.10" not in key
    assert key.startswith("search:client:")
    assert rate_limit_identity("203.0.113.10") in key
