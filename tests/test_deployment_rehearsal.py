from datetime import date
import json
from pathlib import Path

from pipeline.sir_saathi_pipeline.deployment_rehearsal import create_template, main, validate_evidence


def completed_evidence() -> dict:
    evidence = create_template()
    evidence.update({
        "deployed_commit": "b" * 40,
        "deployed_origin": "https://sirsaathi.org",
        "operator": "Release operator",
        "reviewed_by": "Independent reviewer",
        "rehearsal_date": "2026-08-01",
        "no_voter_data_attestation": True,
        "public_search_disabled_attestation": True,
        "deployment_probe": {
            "ready": True,
            "checks_passed": 90,
            "checks_total": 90,
            "blockers": [],
            "release_commit": "b" * 40,
            "values_redacted": True,
        },
    })
    for check in evidence["checks"]:
        check.update({"result": "pass", "evidence": "Private rehearsal record reference."})
    return evidence


def test_template_starts_unreviewed_and_fails_closed() -> None:
    template = create_template()
    assert template["deployment_mode"] == "guidance"
    assert template["no_voter_data_attestation"] is False
    assert template["public_search_disabled_attestation"] is False
    assert template["deployment_probe"] is None
    assert all(item["result"] == "not_tested" for item in template["checks"])

    report = validate_evidence(template, today=date(2026, 8, 1))
    assert report["ready_for_guidance_rehearsal_signoff"] is False
    assert report["required_check_count"] == 12
    assert "evidence.no_voter_data_attestation" in report["blockers"]
    assert "check.release_build.not_tested" in report["blockers"]
    assert "check.accessibility_feedback.not_tested" in report["blockers"]


def test_complete_evidence_passes_without_exposing_private_values() -> None:
    evidence = completed_evidence()
    evidence["checks"][0]["evidence"] = "private-release-ticket-123"
    report = validate_evidence(evidence, today=date(2026, 8, 1))
    assert report == {
        "ready_for_guidance_rehearsal_signoff": True,
        "blockers": [],
        "required_check_count": 12,
        "values_redacted": True,
    }
    assert "private-release-ticket-123" not in str(report)
    assert "Release operator" not in str(report)
    assert "sirsaathi.org" not in str(report)


def test_rehearsal_requires_independent_review_and_safe_scope() -> None:
    evidence = completed_evidence()
    evidence["scope"] = "indexed_search"
    evidence["deployment_mode"] = "indexed-search"
    evidence["reviewed_by"] = " release OPERATOR "
    evidence["public_search_disabled_attestation"] = False
    report = validate_evidence(evidence, today=date(2026, 8, 1))
    assert report["blockers"][:4] == [
        "evidence.guidance_only_scope",
        "evidence.guidance_deployment_mode",
        "evidence.independent_reviewer",
        "evidence.public_search_disabled_attestation",
    ]


def test_rehearsal_binds_deployed_pwa_and_api_probe_to_commit() -> None:
    evidence = completed_evidence()
    evidence["deployment_probe"]["release_commit"] = "a" * 40
    report = validate_evidence(evidence, today=date(2026, 8, 1))
    assert "evidence.deployment_probe_release_binding" in report["blockers"]
    evidence["deployment_probe"]["release_commit"] = "b" * 40
    evidence["deployment_probe"]["checks_passed"] = 41
    assert "evidence.deployment_probe_release_binding" in validate_evidence(
        evidence, today=date(2026, 8, 1)
    )["blockers"]


def test_failed_check_requires_remediation_and_passing_retest() -> None:
    evidence = completed_evidence()
    check = evidence["checks"][4]
    check.update({"result": "fail", "evidence": "CSP probe failed.", "remediation": "", "retest_result": "not_tested"})
    blocked = validate_evidence(evidence, today=date(2026, 8, 1))
    assert "check.edge_deployment_probe.incomplete_failure" in blocked["blockers"]
    assert "check.edge_deployment_probe.retest_not_passed" in blocked["blockers"]

    check.update({"remediation": "Corrected the release configuration.", "retest_result": "pass"})
    assert validate_evidence(evidence, today=date(2026, 8, 1))["ready_for_guidance_rehearsal_signoff"] is True


def test_cli_creates_private_unreviewed_template_and_fails_closed(tmp_path: Path, capsys) -> None:
    output = tmp_path / "deployment-rehearsal.json"
    assert main(["--create-template", "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8")) == create_template()
    assert main(["--validate", str(output), "--require-full-pass"]) == 1
    cli_output = capsys.readouterr().out
    assert '\"ready_for_guidance_rehearsal_signoff\": false' in cli_output
    assert str(output) in cli_output
