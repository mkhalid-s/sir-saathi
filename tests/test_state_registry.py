from datetime import date

import pytest

from pipeline.sir_saathi_pipeline import load_all_states
from pipeline.sir_saathi_pipeline.state_registry import parse_state_config


def test_loads_initial_state_registry() -> None:
    states = load_all_states()
    assert {"IN-MH", "IN-WB"}.issubset(states)


def test_maharashtra_registry_dates_and_capability() -> None:
    mh = load_all_states()["IN-MH"]
    assert mh.eci_state_code == "S13"
    assert mh.schedule.final_roll_date == date(2026, 10, 7)
    assert mh.data_capability == "pilot_indexed_search"
    assert mh.is_search_enabled is True
    assert all(source.last_verified == date(2026, 6, 29) for source in mh.official_sources)
    assert mh.schedule_provenance.confidence == "reported"
    assert mh.schedule_provenance.source_type == "public_report"


def test_west_bengal_starts_guidance_only() -> None:
    wb = load_all_states()["IN-WB"]
    assert wb.eci_state_code == "S25"
    assert wb.data_capability == "guidance_only"
    assert wb.is_search_enabled is False
    assert wb.schedule_provenance.confidence == "official"


def test_all_official_sources_include_freshness_dates() -> None:
    for state in load_all_states().values():
        assert state.official_sources
        for source in state.official_sources:
            assert source.last_verified <= date.today()


def test_schedule_provenance_must_match_listed_source() -> None:
    state = load_all_states()["IN-MH"]
    payload = {
        "state_id": state.state_id,
        "eci_state_code": state.eci_state_code,
        "name": state.name,
        "short_name": state.short_name,
        "languages": list(state.languages),
        "scripts": list(state.scripts),
        "default_language": state.default_language,
        "sir_schedule": {
            "phase": state.schedule.phase,
            "qualifying_date": state.schedule.qualifying_date.isoformat() if state.schedule.qualifying_date else None,
            "enumeration_start": state.schedule.enumeration_start.isoformat() if state.schedule.enumeration_start else None,
            "enumeration_end": state.schedule.enumeration_end.isoformat() if state.schedule.enumeration_end else None,
            "draft_roll_date": state.schedule.draft_roll_date.isoformat() if state.schedule.draft_roll_date else None,
            "claims_start": state.schedule.claims_start.isoformat() if state.schedule.claims_start else None,
            "claims_end": state.schedule.claims_end.isoformat() if state.schedule.claims_end else None,
            "final_roll_date": state.schedule.final_roll_date.isoformat() if state.schedule.final_roll_date else None,
            "status": state.schedule.status,
        },
        "schedule_provenance": {
            "label": "Unknown source",
            "source_type": "public_report",
            "confidence": "reported",
            "notes": "test",
        },
        "ceo_portal": state.ceo_portal,
        "official_sources": [
            {
                "label": source.label,
                "url": source.url,
                "source_type": source.source_type,
                "last_verified": source.last_verified.isoformat(),
                "notes": source.notes,
            }
            for source in state.official_sources
        ],
        "base_roll_years": list(state.base_roll_years),
        "historical_source_shape": state.historical_source_shape,
        "current_roll_source_shape": state.current_roll_source_shape,
        "data_capability": state.data_capability,
        "parser_status": state.parser_status,
        "public_launch_ready": state.public_launch_ready,
        "privacy_notes": state.privacy_notes,
    }
    with pytest.raises(ValueError, match="schedule provenance source is not listed"):
        parse_state_config(payload)
