import pytest

from pipeline.sir_saathi_pipeline.state_registry import load_all_states
from services.api.privacy import (
    PublicSearchPolicy,
    assert_public_search_policy,
    assert_search_launch_allowed,
    safe_log_query,
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


def test_safe_log_query_does_not_store_full_query() -> None:
    assert safe_log_query("Sample Voter Name") == "len:17 prefix:sa"
