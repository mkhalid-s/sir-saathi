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
