from services.api.app import search_payload
from services.api.pilot_data import load_sanitized_pilot_records, validate_pilot_records


def test_sanitized_pilot_records_are_validation_ready() -> None:
    records = load_sanitized_pilot_records()
    summary = validate_pilot_records(records)
    assert summary == {"total": 3, "redaction_ready": 3, "scoped": 3}


def test_api_search_defaults_to_sanitized_pilot_records() -> None:
    result = search_payload({"state_id": "IN-MH", "query": "sample", "ac_number": 172})
    assert result["count"] == 1
    assert result["results"][0]["display_name"] == "Sample Voter"
    assert result["results"][0]["epic_hint"] == "***1234"


def test_scoped_search_does_not_cross_ac_boundaries() -> None:
    result = search_payload({"state_id": "IN-MH", "query": "demo", "ac_number": 172})
    assert result["count"] == 0
