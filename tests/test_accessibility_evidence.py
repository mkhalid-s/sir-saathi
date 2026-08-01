from datetime import date
import json
from pathlib import Path

from pipeline.sir_saathi_pipeline.accessibility_evidence import create_template, main, validate_evidence


def completed_evidence() -> dict:
    evidence = create_template()
    evidence.update({
        "deployed_commit": "a" * 40,
        "deployed_origin": "https://sirsaathi.org",
        "reviewer": "Accessibility reviewer",
        "review_date": "2026-08-01",
        "publishable_locales_tested": ["en"],
        "privacy_attestation": True,
    })
    for environment in evidence["environments"]:
        environment.update({
            "os": "Synthetic test OS",
            "os_version": "1",
            "browser": "Synthetic browser",
            "browser_version": "1",
            "assistive_technology": "Keyboard" if environment["id"] == "keyboard_desktop" else "Synthetic AT",
            "assistive_technology_version": "1",
            "result": "pass",
            "evidence": "Completed the required journey with synthetic data.",
        })
    for check in evidence["checks"]:
        check.update({"result": "pass", "evidence": "Observed expected behavior with synthetic data."})
    return evidence


def test_template_starts_unreviewed_and_fails_closed() -> None:
    template = create_template()
    assert template["reviewer"] is None
    assert template["privacy_attestation"] is False
    assert all(item["result"] == "not_tested" for item in template["checks"])
    assert all(item["result"] == "not_tested" for item in template["environments"])

    report = validate_evidence(template, today=date(2026, 8, 1))
    assert report["ready_for_accessibility_signoff"] is False
    assert report["required_check_count"] == 11
    assert report["required_environment_count"] == 4
    assert "evidence.reviewer" in report["blockers"]
    assert "check.keyboard_navigation.not_tested" in report["blockers"]


def test_complete_manual_evidence_can_pass_without_exposing_values() -> None:
    evidence = completed_evidence()
    evidence["environments"][0]["evidence"] = "private-manual-session-note"
    report = validate_evidence(evidence, today=date(2026, 8, 1))
    assert report == {
        "ready_for_accessibility_signoff": True,
        "blockers": [],
        "required_check_count": 11,
        "required_environment_count": 4,
        "values_redacted": True,
    }
    assert "private-manual-session-note" not in str(report)
    assert "Accessibility reviewer" not in str(report)
    assert "sirsaathi.org" not in str(report)


def test_failure_requires_remediation_and_passing_retest() -> None:
    evidence = completed_evidence()
    check = evidence["checks"][0]
    check.update({"result": "fail", "evidence": "Focus was obscured.", "remediation": "", "retest_result": "not_tested"})
    blocked = validate_evidence(evidence, today=date(2026, 8, 1))
    assert "check.keyboard_navigation.incomplete_failure" in blocked["blockers"]
    assert "check.keyboard_navigation.retest_not_passed" in blocked["blockers"]

    check.update({"remediation": "Fixed in reviewed release ticket A11Y-1.", "retest_result": "pass"})
    assert validate_evidence(evidence, today=date(2026, 8, 1))["ready_for_accessibility_signoff"] is True


def test_validator_rejects_wrong_scope_locale_set_and_future_review() -> None:
    evidence = completed_evidence()
    evidence["scope"] = "focused_retest"
    evidence["publishable_locales_tested"] = []
    evidence["review_date"] = "2026-08-02"
    report = validate_evidence(evidence, today=date(2026, 8, 1))
    assert report["blockers"][:3] == [
        "evidence.full_release_scope",
        "evidence.review_date_future",
        "evidence.publishable_locale_coverage",
    ]


def test_cli_creates_unreviewed_template_and_redacts_validation_output(tmp_path: Path, capsys) -> None:
    output = tmp_path / "accessibility.json"
    assert main(["--create-template", "--output", str(output)]) == 0
    created = json.loads(output.read_text(encoding="utf-8"))
    assert created == create_template()
    assert main(["--validate", str(output), "--require-full-pass"]) == 1
    cli_output = capsys.readouterr().out
    assert '"ready_for_accessibility_signoff": false' in cli_output
    assert str(output) in cli_output  # Creation reports only the operator-selected path.
