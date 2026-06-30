import json
from pathlib import Path

from pipeline.sir_saathi_pipeline import operator_workflow
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


def request(**overrides):
    values = {
        "state_id": "IN-MH",
        "ac_number": 172,
        "pdf_path": Path("data/local/pilot.pdf"),
        "part_number": 21,
        "test_name_env": "SIR_SAATHI_TEST_NAME",
    }
    values.update(overrides)
    return operator_workflow.WorkflowRequest(**values)


def test_build_workflow_outputs_ordered_local_commands_without_raw_name() -> None:
    report = operator_workflow.build_workflow(request(), states=load_all_states())
    commands = [step["command"] for step in report["steps"]]
    encoded = json.dumps(report)

    assert report["local_only"] is True
    assert report["safe_for_public"] is False
    assert report["blockers"] == []
    assert [step["id"] for step in report["steps"]] == [
        "seed_states",
        "dry_run_pdf",
        "load_pdf",
        "validate_search",
        "readiness_report",
    ]
    assert "pipeline.sir_saathi_pipeline.seed_states" in commands[0]
    assert "--dry-run" in commands[1]
    assert "--load" in commands[2]
    assert "pipeline.sir_saathi_pipeline.local_search" in commands[3]
    assert "pipeline.sir_saathi_pipeline.readiness_report" in commands[4]
    assert "--part 21" in commands[4]
    assert "${SIR_SAATHI_TEST_NAME}" in encoded
    assert "Hidden Query" not in encoded
    assert "epic_hash" not in encoded


def test_build_workflow_reports_state_config_and_required_env() -> None:
    report = operator_workflow.build_workflow(request(), states=load_all_states())

    assert report["required_env"] == [
        operator_workflow.DATABASE_URL_ENV,
        operator_workflow.EPIC_HASH_SALT_ENV,
        operator_workflow.DEFAULT_TEST_NAME_ENV,
    ]
    assert report["state_config"]["data_capability"] == "pilot_indexed_search"
    assert report["state_config"]["public_launch_ready"] is False
    assert report["state_config"]["schedule_provenance"] == "reported"


def test_workflow_request_validates_state_scope_and_local_pdf_path() -> None:
    states = load_all_states()

    assert request(state_id="IN-XX").validate(states) == ["unknown state_id: IN-XX"]
    assert "ac_number must be positive" in request(ac_number=0).validate(states)
    assert "part_number must be positive" in request(part_number=0).validate(states)
    assert any(
        "pdf path must be repo-relative" in blocker
        for blocker in request(pdf_path=Path("/tmp/pilot.pdf")).validate(states)
    )
    assert "pdf path should stay under ignored data/ or samples/ directories" in request(pdf_path=Path("docs/pilot.pdf")).validate(states)
    assert "test name env var" in request(test_name_env="bad-name").validate(states)[0]


def test_main_returns_nonzero_when_blockers_exist(capsys) -> None:
    exit_code = operator_workflow.main([
        "--state", "IN-XX",
        "--ac", "172",
        "--pdf", "data/local/pilot.pdf",
    ])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["local_only"] is True
    assert output["safe_for_public"] is False
    assert "unknown state_id: IN-XX" in output["blockers"]


def test_main_returns_safe_workflow(capsys) -> None:
    exit_code = operator_workflow.main([
        "--state", "IN-MH",
        "--ac", "172",
        "--part", "21",
        "--pdf", "data/local/pilot.pdf",
        "--test-name-env", "SIR_SAATHI_TEST_NAME",
    ])
    output = json.loads(capsys.readouterr().out)
    encoded = json.dumps(output)

    assert exit_code == 0
    assert output["blockers"] == []
    assert len(output["steps"]) == 5
    assert "data/local/pilot.pdf" in encoded
    assert "SIR_SAATHI_TEST_NAME" in encoded
    assert "voter_name" not in encoded
