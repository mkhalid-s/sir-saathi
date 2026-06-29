import pytest

from services.api.privacy import PublicSearchPolicy, assert_public_search_policy, safe_log_query


def test_default_public_search_policy_is_safe() -> None:
    assert_public_search_policy()


def test_policy_blocks_bulk_export() -> None:
    with pytest.raises(ValueError):
        assert_public_search_policy(PublicSearchPolicy(allow_bulk_export=True))


def test_policy_blocks_unscoped_public_search() -> None:
    with pytest.raises(ValueError):
        assert_public_search_policy(PublicSearchPolicy(require_scope=False))


def test_safe_log_query_does_not_store_full_query() -> None:
    assert safe_log_query("Sample Voter Name") == "len:17 prefix:sa"
