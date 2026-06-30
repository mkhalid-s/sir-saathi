import json
from pathlib import Path

from pipeline.sir_saathi_pipeline import operator_workflow
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


def write_manifest(tmp_path: Path) -> Path:
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "mh-2002-ac172-part21",
                        "state_id": "IN-MH",
                        "roll_year": 2002,
                        "roll_kind": "historical_base_roll",
                        "source_label": "Synthetic reviewed source",
                        "source_uri": "https://example.test/official.pdf",
                        "local_path": "data/local/pilot.pdf",
                        "parser_hint": "parse_2002",
                        "language": "mr",
                        "reviewed": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def request(**overrides):
    values = {
        "state_id": "IN-MH",
        "ac_number": 172,
        "pdf_path": Path("data/local/pilot.pdf"),
        "part_number": 21,
        "test_name_env": "SIR_SAATHI_TEST_NAME",
        "manifest_path": Path("sources.json"),
        "source_id": "mh-2002-ac172-part21",
    }
    values.update(overrides)
    return operator_workflow.WorkflowRequest(**values)


def test_build_workflow_outputs_ordered_local_commands_without_raw_name(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)
    report = operator_workflow.build_workflow(request(manifest_path=manifest_path), states=load_all_states())
    commands = [step["command"] for step in report["steps"]]
    encoded = json.dumps(report)

    assert report["local_only"] is True
    assert report["safe_for_public"] is False
    assert report["blockers"] == []
    assert [step["id"] for step in report["steps"]] == [
        "seed_states",
        "validate_source_manifest",
        "dry_run_pdf",
        "load_pdf",
        "validate_search",
        "readiness_report",
    ]
    assert "pipeline.sir_saathi_pipeline.seed_states" in commands[0]
    assert "pipeline.sir_saathi_pipeline.sources" in commands[1]
    assert "--dry-run" in commands[2]
    assert "--roll-year 2002" in commands[2]
    assert "--source-label 'Synthetic reviewed source'" in commands[2]
    assert "--load" in commands[3]
    assert "pipeline.sir_saathi_pipeline.local_search" in commands[4]
    assert "pipeline.sir_saathi_pipeline.readiness_report" in commands[5]
    assert "--part 21" in commands[5]
    assert "${SIR_SAATHI_TEST_NAME}" in encoded
    assert "Hidden Query" not in encoded
    assert "epic_hash" not in encoded


def test_build_workflow_reports_state_config_and_required_env(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)
    report = operator_workflow.build_workflow(request(manifest_path=manifest_path), states=load_all_states())

    assert report["required_env"] == [
        operator_workflow.DATABASE_URL_ENV,
        operator_workflow.EPIC_HASH_SALT_ENV,
        operator_workflow.DEFAULT_TEST_NAME_ENV,
    ]
    assert report["state_config"]["data_capability"] == "pilot_indexed_search"
    assert report["state_config"]["public_launch_ready"] is False
    assert report["state_config"]["schedule_provenance"] == "reported"
    assert report["source_manifest"]["reviewed"] is True
    assert report["source_manifest"]["roll_year"] == 2002


def test_workflow_request_validates_state_scope_and_local_pdf_path() -> None:
    states = load_all_states()

    assert "unknown state_id: IN-XX" in request(state_id="IN-XX").validate(states)
    assert "ac_number must be positive" in request(ac_number=0).validate(states)
    assert "part_number must be positive" in request(part_number=0).validate(states)
    assert any(
        "pdf path must be repo-relative" in blocker
        for blocker in request(pdf_path=Path("/tmp/pilot.pdf")).validate(states)
    )
    assert "pdf path should stay under ignored data/ or samples/ directories" in request(pdf_path=Path("docs/pilot.pdf")).validate(states)
    assert "test name env var" in request(test_name_env="bad-name").validate(states)[0]
    assert "source manifest and source id are required before onboarding" in request(manifest_path=None, source_id=None).validate(states)


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


def test_main_returns_safe_workflow(capsys, tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)
    exit_code = operator_workflow.main([
        "--state", "IN-MH",
        "--ac", "172",
        "--part", "21",
        "--pdf", "data/local/pilot.pdf",
        "--test-name-env", "SIR_SAATHI_TEST_NAME",
        "--manifest", str(manifest_path),
        "--source-id", "mh-2002-ac172-part21",
    ])
    output = json.loads(capsys.readouterr().out)
    encoded = json.dumps(output)

    assert exit_code == 0
    assert output["blockers"] == []
    assert len(output["steps"]) == 6
    assert "data/local/pilot.pdf" in encoded
    assert "SIR_SAATHI_TEST_NAME" in encoded
    assert "voter_name" not in encoded
