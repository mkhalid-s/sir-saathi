from datetime import date

from pipeline.sir_saathi_pipeline.source_freshness import assess_source, build_freshness_report, main
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


def test_current_nationwide_sources_pass_risk_based_freshness_policy() -> None:
    report = build_freshness_report(today=date(2026, 8, 1))
    assert report["jurisdiction_count"] == 36
    assert report["source_count"] == 131
    assert report["stale_count"] == 0
    assert report["ready"] is True


def test_active_schedule_sources_expire_after_seven_days() -> None:
    report = build_freshness_report(today=date(2026, 8, 9))
    stale = report["stale"]
    assert report["ready"] is False
    assert {finding["state_id"] for finding in stale} == {
        "IN-AP", "IN-AR", "IN-CH", "IN-DH", "IN-DL", "IN-HR", "IN-JH", "IN-KA", "IN-MH",
        "IN-ML", "IN-MN", "IN-MZ", "IN-NL", "IN-OD", "IN-PB", "IN-SK", "IN-TG", "IN-TR", "IN-UK",
    }
    assert all(finding["age_days"] == 8 for finding in stale)
    assert all(finding["max_age_days"] == 7 for finding in stale)


def test_future_verification_dates_fail_closed() -> None:
    state = load_all_states()["IN-MH"]
    finding = assess_source(state, state.official_sources[0], date(2026, 7, 31))
    assert finding.stale is True
    assert finding.as_dict()["status"] == "invalid_future_date"


def test_freshness_cli_can_fail_closed_without_private_data(capsys) -> None:
    assert main(["--today", "2026-08-09", "--fail-on-stale"]) == 1
    output = capsys.readouterr().out
    assert '"ready": false' in output
    assert '"state_id": "IN-MH"' in output
    assert "epic" not in output.casefold()
