"""Local operator workflow planner for onboarding a SIR roll slice."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import shlex
from typing import Any

from pipeline.sir_saathi_pipeline.state_registry import StateConfig, load_all_states

DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"
EPIC_HASH_SALT_ENV = "SIR_SAATHI_EPIC_HASH_SALT"
DEFAULT_TEST_NAME_ENV = "SIR_SAATHI_TEST_NAME"


@dataclass(frozen=True)
class WorkflowRequest:
    state_id: str
    ac_number: int
    pdf_path: Path
    part_number: int | None = None
    test_name_env: str = DEFAULT_TEST_NAME_ENV

    def validate(self, states: dict[str, StateConfig]) -> list[str]:
        blockers: list[str] = []
        if self.state_id not in states:
            blockers.append(f"unknown state_id: {self.state_id}")
        if self.ac_number <= 0:
            blockers.append("ac_number must be positive")
        if self.part_number is not None and self.part_number <= 0:
            blockers.append("part_number must be positive")
        if not self.test_name_env or not self.test_name_env.replace("_", "").isalnum():
            blockers.append("test name env var must be alphanumeric with underscores")
        if self.pdf_path.is_absolute():
            blockers.append("pdf path must be repo-relative so raw local paths are not printed")
        if self.pdf_path.parts and self.pdf_path.parts[0] not in {"data", "samples"}:
            blockers.append("pdf path should stay under ignored data/ or samples/ directories")
        return blockers


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def env_exports() -> list[str]:
    return [DATABASE_URL_ENV, EPIC_HASH_SALT_ENV]


def step(step_id: str, title: str, command: str, *, requires_env: list[str], safety: str) -> dict[str, Any]:
    return {
        "id": step_id,
        "title": title,
        "command": command,
        "requires_env": requires_env,
        "safety": safety,
    }


def build_workflow(request: WorkflowRequest, *, states: dict[str, StateConfig] | None = None) -> dict[str, Any]:
    registry = states or load_all_states()
    blockers = request.validate(registry)
    state = registry.get(request.state_id)
    pdf_arg = request.pdf_path.as_posix()

    seed_command = shell_join([
        "python", "-m", "pipeline.sir_saathi_pipeline.seed_states", "--state", request.state_id
    ])
    dry_run_command = shell_join([
        "python", "-m", "pipeline.sir_saathi_pipeline.ingest_roll",
        "--pdf", pdf_arg,
        "--state", request.state_id,
        "--dry-run",
    ])
    load_command = shell_join([
        "python", "-m", "pipeline.sir_saathi_pipeline.ingest_roll",
        "--pdf", pdf_arg,
        "--state", request.state_id,
        "--load",
    ])
    search_command = shell_join([
        "python", "-m", "pipeline.sir_saathi_pipeline.local_search",
        "--state", request.state_id,
        "--ac", str(request.ac_number),
        "--name", f"${{{request.test_name_env}}}",
    ])
    readiness_parts = [
        "python", "-m", "pipeline.sir_saathi_pipeline.readiness_report",
        "--state", request.state_id,
        "--ac", str(request.ac_number),
    ]
    if request.part_number is not None:
        readiness_parts.extend(["--part", str(request.part_number)])

    workflow_steps = [
        step(
            "seed_states",
            "Seed canonical state metadata",
            seed_command,
            requires_env=[DATABASE_URL_ENV],
            safety="Upserts reviewed state config only; does not invent metadata.",
        ),
        step(
            "dry_run_pdf",
            "Parse and validate PDF without database writes",
            dry_run_command,
            requires_env=[EPIC_HASH_SALT_ENV],
            safety="Builds DB-ready rows and safe counts without exports or DB writes.",
        ),
        step(
            "load_pdf",
            "Load validated roll batch into local Postgres",
            load_command,
            requires_env=[DATABASE_URL_ENV, EPIC_HASH_SALT_ENV],
            safety="Requires explicit --load and writes only to local Postgres.",
        ),
        step(
            "validate_search",
            "Run local redacted search validation",
            search_command,
            requires_env=[DATABASE_URL_ENV, request.test_name_env],
            safety="Uses a name stored in an env var so the workflow report does not print the raw query.",
        ),
        step(
            "readiness_report",
            "Generate local readiness blockers",
            shell_join(readiness_parts),
            requires_env=[DATABASE_URL_ENV],
            safety="Reports safe aggregate readiness and never returns voter rows.",
        ),
    ]

    return {
        "local_only": True,
        "safe_for_public": False,
        "state_id": request.state_id,
        "state_known": state is not None,
        "ac_number": request.ac_number,
        "part_number": request.part_number,
        "pdf_path": pdf_arg,
        "test_name_env": request.test_name_env,
        "required_env": env_exports() + [request.test_name_env],
        "state_config": None if state is None else {
            "data_capability": state.data_capability,
            "public_launch_ready": state.public_launch_ready,
            "schedule_provenance": state.schedule_provenance.confidence,
        },
        "blockers": blockers,
        "steps": workflow_steps,
        "next_decision": "Run readiness_report and resolve blockers before any public search work.",
    }


def failure_report(message: str) -> dict[str, Any]:
    return {
        "local_only": True,
        "safe_for_public": False,
        "error": message,
        "blockers": [message],
        "steps": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan the local SIR roll onboarding workflow.")
    parser.add_argument("--state", required=True, help="Canonical state id, for example IN-MH.")
    parser.add_argument("--ac", required=True, type=int, help="Assembly Constituency number.")
    parser.add_argument("--pdf", required=True, type=Path, help="Repo-relative raw PDF path under ignored data/ or samples/.")
    parser.add_argument("--part", type=int, help="Optional polling part number for readiness scope.")
    parser.add_argument("--test-name-env", default=DEFAULT_TEST_NAME_ENV, help="Env var containing local search test name.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    request = WorkflowRequest(
        state_id=args.state,
        ac_number=args.ac,
        pdf_path=args.pdf,
        part_number=args.part,
        test_name_env=args.test_name_env,
    )
    try:
        report = build_workflow(request)
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
