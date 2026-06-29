from datetime import date

from pipeline.sir_saathi_pipeline import load_all_states


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


def test_west_bengal_starts_guidance_only() -> None:
    wb = load_all_states()["IN-WB"]
    assert wb.eci_state_code == "S25"
    assert wb.data_capability == "guidance_only"
    assert wb.is_search_enabled is False


def test_all_official_sources_include_freshness_dates() -> None:
    for state in load_all_states().values():
        assert state.official_sources
        for source in state.official_sources:
            assert source.last_verified <= date.today()
