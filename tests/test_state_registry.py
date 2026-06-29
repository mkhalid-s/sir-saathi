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


def test_west_bengal_starts_guidance_only() -> None:
    wb = load_all_states()["IN-WB"]
    assert wb.eci_state_code == "S25"
    assert wb.data_capability == "guidance_only"
    assert wb.is_search_enabled is False
