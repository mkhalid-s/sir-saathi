from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_slice_gate_and_operating_model_exist() -> None:
    assert (ROOT / "scripts" / "slice_gate.py").is_file()
    assert (ROOT / "docs" / "AGENT_TEAM_OPERATING_MODEL.md").is_file()


def test_slice_gate_checks_expected_commands() -> None:
    gate = (ROOT / "scripts" / "slice_gate.py").read_text(encoding="utf-8")
    assert "scripts/check_sensitive.py" in gate
    assert "pytest" in gate
    assert "npm" in gate
    assert "scripts/launch_gate.py" in gate


def test_launch_gate_audits_generated_discoverability() -> None:
    gate = (ROOT / "scripts/launch_gate.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "scripts/check_discoverability.py" in gate
    assert "scripts/check_discoverability.py" in workflow


def test_official_source_freshness_has_an_unattended_fail_closed_monitor() -> None:
    workflow = (ROOT / ".github/workflows/source-freshness.yml").read_text(encoding="utf-8")

    assert "schedule:" in workflow
    assert "cron: '17 3 * * *'" in workflow
    assert "workflow_dispatch:" in workflow
    assert "--fail-on-stale" in workflow
    assert "if: always()" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "retention-days: 30" in workflow
