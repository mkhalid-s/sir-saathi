import pytest
from services.api.app import api_route_paths, guidance_payload, list_states_payload, search_payload
from services.api.models import InternalVoterRecord, redact_voter_record
from services.api.privacy import InMemoryRateLimiter
from services.api.schemas import ValidationError


def test_api_routes_are_prefixed_for_proxy() -> None:
    paths = api_route_paths()
    assert "/api/health" in paths
    assert "/api/states" in paths
    assert "/api/guidance" in paths
    assert "/api/search" in paths
    assert "/health" not in paths


def test_list_states_payload_exposes_registry_without_private_data() -> None:
    states = list_states_payload()
    mh = next(state for state in states if state["state_id"] == "IN-MH")
    assert mh["data_capability"] == "pilot_indexed_search"
    assert "final_roll_date" in mh


def test_guidance_payload_returns_deadline_string() -> None:
    result = guidance_payload({"state_id": "IN-MH", "situation": "missing_name"})
    assert result["priority"] == "urgent"
    assert result["deadline"] == "2026-09-04"


def test_guidance_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        guidance_payload({"state_id": "IN-MH", "situation": "missing_name", "extra": "nope"})


def test_search_requires_ac_scope() -> None:
    with pytest.raises(ValidationError):
        search_payload({"state_id": "IN-MH", "query": "sample", "use_sanitized_pilot": True})


def test_search_fails_closed_without_public_launch_or_pilot_flag() -> None:
    with pytest.raises(ValueError, match="not enabled for public launch"):
        search_payload({"state_id": "IN-MH", "query": "sample", "ac_number": 172})


def test_search_requires_typed_query() -> None:
    with pytest.raises(ValidationError):
        search_payload({"state_id": "IN-MH", "query": 123, "ac_number": 172, "use_sanitized_pilot": True})


def test_search_returns_redacted_records_with_explicit_pilot_flag() -> None:
    records = [
        InternalVoterRecord(
            state_id="IN-MH",
            ac_number=172,
            part_number=21,
            serial_number=12,
            name="Sample Voter",
            roll_year=2002,
            roll_kind="base_roll",
            data_quality="ok",
            source_label="sanitized fixture",
            confidence=0.99,
            epic_last4="1234",
        )
    ]
    result = search_payload(
        {"state_id": "IN-MH", "query": "sample", "ac_number": 172, "use_sanitized_pilot": True},
        records,
    )
    assert result["count"] == 1
    assert result["results"][0]["epic_hint"] == "***1234"
    assert "epic_number" not in result["results"][0]


def test_search_payload_applies_rate_limit_when_limiter_is_provided() -> None:
    records = [
        InternalVoterRecord(
            state_id="IN-MH",
            ac_number=172,
            part_number=21,
            serial_number=12,
            name="Sample Voter",
            roll_year=2002,
            roll_kind="base_roll",
            data_quality="ok",
            source_label="sanitized fixture",
            confidence=0.99,
            epic_last4="1234",
        )
    ]
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60)
    payload = {"state_id": "IN-MH", "query": "sample", "ac_number": 172, "use_sanitized_pilot": True}
    assert search_payload(payload, records, rate_limiter=limiter, client_identity="client-a")["count"] == 1
    with pytest.raises(ValueError, match="search rate limit exceeded"):
        search_payload(payload, records, rate_limiter=limiter, client_identity="client-a")


def test_redaction_does_not_expose_internal_epic_field() -> None:
    public = redact_voter_record(
        InternalVoterRecord(
            state_id="IN-MH",
            ac_number=None,
            part_number=None,
            serial_number=None,
            name="Sample Voter",
            roll_year=2026,
            roll_kind="draft_roll",
            data_quality="ok",
            source_label="test",
            confidence=0.7,
            epic_last4=None,
        )
    ).to_dict()
    assert public["epic_hint"] is None
