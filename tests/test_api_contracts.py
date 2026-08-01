from datetime import date

import pytest
from services.api.app import assistance_payload, api_route_paths, create_app, forms_payload, guidance_payload, list_states_payload, search_payload
from services.api.body_limit import BoundedApiBodyMiddleware, MAX_API_BODY_BYTES
from services.api.models import InternalVoterRecord, redact_voter_record
from services.api.privacy import InMemoryRateLimiter
from services.api.schemas import ValidationError


def test_api_routes_are_prefixed_for_proxy() -> None:
    paths = api_route_paths()
    assert "/api/health" in paths
    assert "/api/ready" in paths
    assert "/api/states" in paths
    assert "/api/forms" in paths
    assert "/api/assistance" in paths
    assert "/api/guidance" in paths
    assert "/api/search" in paths
    assert "/health" not in paths


def test_api_installs_the_preparser_request_body_limit() -> None:
    app = create_app()
    middleware = next(item for item in app.user_middleware if item.cls is BoundedApiBodyMiddleware)
    assert middleware.kwargs["max_bytes"] == MAX_API_BODY_BYTES == 16 * 1024


def test_list_states_payload_exposes_registry_without_private_data() -> None:
    states = list_states_payload(today=date(2026, 8, 1))
    assert len(states) == 36
    mh = next(state for state in states if state["state_id"] == "IN-MH")
    assert mh["data_capability"] == "pilot_indexed_search"
    assert "final_roll_date" in mh
    assert mh["ceo_portal"] == "https://ceoelection.maharashtra.gov.in/"
    assert mh["sir_schedule"]["enumeration_end"] == "2026-07-29"
    assert mh["sir_schedule"]["claims_end"] == "2026-09-04"
    assert mh["sir_schedule"]["final_roll_date"] == "2026-10-07"
    assert mh["schedule_provenance"]["confidence"] == "official"
    assert mh["schedule_provenance"]["source_type"] == "official_portal"
    assert mh["official_sources"][0]["last_verified"] == "2026-08-01"
    assert mh["official_sources"][0]["freshness"] == "fresh"
    assert mh["official_sources"][0]["age_days"] == 0
    assert mh["source_freshness_policy_days"] == 7
    assert mh["current_phase"] == "pre_draft_publication"
    assert mh["sir_schedule"]["current_phase"] == "pre_draft_publication"

    ap = next(state for state in states if state["state_id"] == "IN-AP")
    assert ap["data_capability"] == "official_link_search"
    assert ap["current_phase"] == "claims_and_objections_open"
    assert ap["schedule_provenance"]["confidence"] == "official"
    assert ap["sir_schedule"]["final_roll_date"] == "2026-09-22"
    assert ap["source_freshness_policy_days"] == 7


def test_forms_payload_exposes_canonical_forms_without_user_data() -> None:
    payload = forms_payload()
    labels = {form["form_id"]: form["label"] for form in payload["forms"]}
    assert labels["enumeration_form"] == "SIR Enumeration Form"
    assert labels["form_7"] == "Form 7"
    assert "address" in payload["common_documents"]
    assert "epic_number" not in str(payload).casefold()
    assert payload["locale_used"] == "en"
    assert payload["locale_fallback"] is False


def test_assistance_payload_exposes_only_governed_official_channels() -> None:
    payload = assistance_payload()
    assert {source["url"] for source in payload["sources"]} == {
        "https://voters.eci.gov.in/", "https://www.eci.gov.in/contact-us"
    }
    assert all(source["last_verified"] == "2026-08-01" for source in payload["sources"])
    assert {channel["channel_id"] for channel in payload["channels"]} == {"portal", "helpline", "email"}
    assert next(channel for channel in payload["channels"] if channel["channel_id"] == "helpline")["href"] == "tel:1950"
    assert next(channel for channel in payload["channels"] if channel["channel_id"] == "email")["href"] == "mailto:complaints@eci.gov.in"
    assert all(channel["source_ids"] for channel in payload["channels"])
    assert "epic" not in str(payload).casefold()

    fallback = assistance_payload("mr")
    assert fallback["locale_requested"] == "mr"
    assert fallback["locale_used"] == "en"
    assert fallback["locale_fallback"] is True


def test_api_locale_negotiation_is_explicit_and_fail_closed() -> None:
    forms = forms_payload("mr")
    assert forms["locale_requested"] == "mr"
    assert forms["locale_used"] == "en"
    assert forms["locale_fallback"] is True

    states = list_states_payload(today=date(2026, 8, 1), locale="zz")
    assert all(state["locale_requested"] == "zz" for state in states)
    assert all(state["locale_used"] == "en" and state["locale_fallback"] for state in states)
    mh = next(state for state in states if state["state_id"] == "IN-MH")
    assert mh["current_phase_label"] == "Draft roll publication is next"

    guidance = guidance_payload(
        {"state_id": "IN-MH", "situation": "missing_name", "locale": "mr"},
        today=date(2026, 8, 1),
    )
    assert guidance["locale_requested"] == "mr"
    assert guidance["locale_used"] == "en"
    assert guidance["locale_fallback"] is True
    assert guidance["title"] == "Act quickly on a missing name"


def test_guidance_payload_returns_deadline_string() -> None:
    result = guidance_payload(
        {"state_id": "IN-MH", "situation": "missing_name"},
        today=date(2026, 8, 1),
    )
    assert result["priority"] == "urgent"
    assert result["deadline"] == "2026-09-04"


def test_guidance_payload_moves_past_expired_enumeration_deadline() -> None:
    result = guidance_payload(
        {"state_id": "IN-MH", "situation": "existing_voter"},
        today=date(2026, 8, 1),
    )
    assert result["deadline"] == "2026-09-04"


def test_guidance_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        guidance_payload({"state_id": "IN-MH", "situation": "missing_name", "extra": "nope"})


def test_guidance_rejects_malformed_locale_codes() -> None:
    with pytest.raises(ValidationError, match="locale"):
        guidance_payload({"state_id": "IN-MH", "situation": "missing_name", "locale": "en-US"})


def test_search_requires_ac_scope() -> None:
    with pytest.raises(ValidationError):
        search_payload({"state_id": "IN-MH", "query": "sample", "use_sanitized_pilot": True})


def test_search_fails_closed_without_public_launch_or_pilot_flag() -> None:
    with pytest.raises(ValueError, match="not enabled for public launch"):
        search_payload({"state_id": "IN-MH", "query": "sample", "ac_number": 172})


def test_search_requires_typed_query() -> None:
    with pytest.raises(ValidationError):
        search_payload({"state_id": "IN-MH", "query": 123, "ac_number": 172, "use_sanitized_pilot": True})


def test_search_rejects_client_claimed_verification_boolean() -> None:
    with pytest.raises(ValidationError, match="unknown fields: turnstile_verified"):
        search_payload(
            {
                "state_id": "IN-MH",
                "query": "sample",
                "ac_number": 172,
                "turnstile_verified": True,
            }
        )


def test_search_accepts_only_bounded_opaque_verification_response() -> None:
    with pytest.raises(ValidationError, match="turnstile_response must be a string"):
        search_payload(
            {
                "state_id": "IN-MH",
                "query": "sample",
                "ac_number": 172,
                "turnstile_response": True,
            }
        )


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
