from datetime import date
import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline import load_all_states
from pipeline.sir_saathi_pipeline.state_registry import parse_state_config

ROOT = Path(__file__).resolve().parents[1]


def test_loads_initial_state_registry() -> None:
    states = load_all_states()
    assert len(states) == 36
    assert set(states) == {
        "IN-AN", "IN-AP", "IN-AR", "IN-AS", "IN-BR", "IN-CG", "IN-CH", "IN-DH", "IN-DL",
        "IN-GA", "IN-GJ", "IN-HP", "IN-HR", "IN-JH", "IN-JK", "IN-KA", "IN-KL", "IN-LA",
        "IN-LD", "IN-MH", "IN-ML", "IN-MN", "IN-MP", "IN-MZ", "IN-NL", "IN-OD", "IN-PB",
        "IN-PY", "IN-RJ", "IN-SK", "IN-TG", "IN-TN", "IN-TR", "IN-UK", "IN-UP", "IN-WB",
    }


def test_nationwide_baselines_are_official_link_only_and_unverified() -> None:
    states = load_all_states()
    baseline = states["IN-HP"]
    assert baseline.data_capability == "official_link_search"
    assert baseline.public_launch_ready is False
    assert baseline.schedule.status == "schedule_unverified"
    assert baseline.schedule_provenance.confidence == "unverified"
    assert baseline.schedule.final_roll_date is None
    assert baseline.ceo_portal == "https://ceohimachal.hp.gov.in"
    assert any(source.label == "ECI CEO contact directory" for source in baseline.official_sources)


def test_phase_three_schedule_is_shared_across_19_reviewed_jurisdictions() -> None:
    states = load_all_states()
    phase_three = {state_id for state_id, state in states.items() if state.schedule.phase == "Phase III"}

    assert phase_three == {
        "IN-AP", "IN-AR", "IN-CH", "IN-DH", "IN-DL", "IN-HR", "IN-JH", "IN-KA", "IN-MH",
        "IN-ML", "IN-MN", "IN-MZ", "IN-NL", "IN-OD", "IN-PB", "IN-SK", "IN-TG", "IN-TR", "IN-UK",
    }
    assert all(states[state_id].schedule_provenance.confidence == "official" for state_id in phase_three)
    assert states["IN-AP"].schedule.final_roll_date == date(2026, 9, 22)
    assert states["IN-NL"].schedule.enumeration_start == date(2026, 8, 16)
    assert states["IN-TR"].schedule.final_roll_date == date(2026, 12, 23)
    assert all(states[state_id].public_launch_ready is False for state_id in phase_three)


def test_completed_phase_two_and_assam_dates_use_final_publication_evidence() -> None:
    states = load_all_states()
    assert states["IN-GA"].schedule.final_roll_date == date(2026, 2, 21)
    assert states["IN-CG"].schedule.final_roll_date == date(2026, 2, 21)
    assert states["IN-RJ"].schedule.final_roll_date == date(2026, 2, 21)
    assert states["IN-KL"].schedule.final_roll_date == date(2026, 2, 21)
    assert states["IN-TN"].schedule.final_roll_date == date(2026, 2, 17)
    assert states["IN-PY"].schedule.final_roll_date == date(2026, 2, 14)
    assert states["IN-AS"].schedule.final_roll_date == date(2026, 2, 10)
    assert states["IN-AS"].schedule.phase == "Special Revision 2026"
    assert all(
        states[state_id].schedule.status_on(date(2026, 8, 1)) == "final_roll_published"
        for state_id in {"IN-AS", "IN-CG", "IN-GA", "IN-KL", "IN-PY", "IN-RJ", "IN-TN"}
    )


def test_reviewed_schedule_coverage_fails_closed_for_only_three_jurisdictions() -> None:
    states = load_all_states()
    official = {state_id for state_id, state in states.items() if state.schedule_provenance.confidence == "official"}
    unverified = set(states) - official

    assert len(official) == 33
    assert unverified == {"IN-HP", "IN-JK", "IN-LA"}
    assert states["IN-BR"].schedule.final_roll_date == date(2025, 9, 30)
    assert states["IN-GJ"].schedule.final_roll_date == date(2026, 2, 17)
    assert states["IN-UP"].schedule.final_roll_date == date(2026, 4, 10)
    assert states["IN-LD"].schedule.final_roll_date == date(2026, 2, 14)


def test_nationwide_registry_has_unique_eci_codes_and_valid_language_defaults() -> None:
    states = load_all_states()
    assert len({state.eci_state_code for state in states.values()}) == 36
    for state in states.values():
        assert state.default_language in state.languages
        assert state.languages
        assert state.scripts


def test_every_nationwide_language_has_a_governed_locale() -> None:
    locale_data = json.loads((ROOT / "config/locales.json").read_text(encoding="utf-8"))
    locales = {locale["code"]: locale for locale in locale_data["locales"]}
    state_languages = {language for state in load_all_states().values() for language in state.languages}
    assert state_languages <= set(locales)
    assert locales["en"] == {"code": "en", "label": "English", "status": "available", "review": "reviewed"}
    assert all(
        locale["status"] == "planned" and locale["review"] == "required"
        for code, locale in locales.items()
        if code != "en"
    )


def test_maharashtra_registry_dates_and_capability() -> None:
    mh = load_all_states()["IN-MH"]
    assert mh.eci_state_code == "S13"
    assert mh.schedule.final_roll_date == date(2026, 10, 7)
    assert mh.data_capability == "pilot_indexed_search"
    assert mh.is_search_enabled is True
    assert all(source.last_verified == date(2026, 8, 1) for source in mh.official_sources)
    assert mh.schedule_provenance.confidence == "official"
    assert mh.schedule_provenance.source_type == "official_portal"


def test_maharashtra_schedule_derives_current_phase_from_dates() -> None:
    schedule = load_all_states()["IN-MH"].schedule
    assert schedule.status_on(date(2026, 6, 29)) == "pre_enumeration"
    assert schedule.status_on(date(2026, 7, 1)) == "enumeration_open"
    assert schedule.status_on(date(2026, 8, 1)) == "pre_draft_publication"
    assert schedule.status_on(date(2026, 8, 5)) == "claims_and_objections_open"
    assert schedule.status_on(date(2026, 9, 5)) == "claims_disposal"
    assert schedule.status_on(date(2026, 10, 7)) == "final_roll_published"


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
