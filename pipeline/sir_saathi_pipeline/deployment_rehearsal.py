"""Create and validate private guidance-only deployment rehearsal evidence."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

from .deployment_preflight import _public_origin
from .translation_catalog import _load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 2
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
RESULTS = {"pass", "fail", "not_tested"}
CHECKS = (
    ("release_build", "Production-origin build, launch gate, and immutable release artifact"),
    ("guidance_preflight", "Guidance-mode production configuration preflight"),
    ("migration_dry_run", "PostgreSQL migration dry run reviewed before apply"),
    ("migration_apply_check", "Migrations applied and checksum history check passed"),
    ("edge_deployment_probe", "Same-origin TLS, routing, headers, CSP, API readiness, and 404 probe"),
    ("offline_install_update", "Install, offline navigation, and service-worker update behavior"),
    ("encrypted_backup_verify", "Encrypted backup creation, checksum, and archive verification"),
    ("isolated_restore_drill", "Isolated PostgreSQL restore with aggregate-only comparison"),
    ("monitoring_alert", "Readiness monitor and alert delivery rehearsal"),
    ("accessibility_evidence", "Manual accessibility evidence validator passed for this release"),
    ("rollback_rehearsal", "Application and static-release rollback rehearsal"),
)


def create_template() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "guidance_only_production_rehearsal",
        "deployment_mode": "guidance",
        "deployed_commit": None,
        "deployed_origin": None,
        "operator": None,
        "reviewed_by": None,
        "rehearsal_date": None,
        "no_voter_data_attestation": False,
        "public_search_disabled_attestation": False,
        "deployment_probe": None,
        "checks": [
            {
                "id": identifier,
                "label": label,
                "result": "not_tested",
                "evidence": "",
                "remediation": "",
                "retest_result": "not_tested",
            }
            for identifier, label in CHECKS
        ],
    }


def _complete_text(value: Any, *, maximum: int = 1000) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def validate_evidence(evidence: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    blockers: list[str] = []
    if evidence.get("schema_version") != SCHEMA_VERSION:
        blockers.append("evidence.schema_version")
    if evidence.get("scope") != "guidance_only_production_rehearsal":
        blockers.append("evidence.guidance_only_scope")
    if evidence.get("deployment_mode") != "guidance":
        blockers.append("evidence.guidance_deployment_mode")
    commit = evidence.get("deployed_commit")
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
        blockers.append("evidence.deployed_commit")
    origin = evidence.get("deployed_origin")
    if not isinstance(origin, str) or not _public_origin(origin)[0]:
        blockers.append("evidence.deployed_https_origin")
    operator = evidence.get("operator")
    reviewer = evidence.get("reviewed_by")
    if not _complete_text(operator, maximum=200):
        blockers.append("evidence.operator")
    if not _complete_text(reviewer, maximum=200):
        blockers.append("evidence.reviewer")
    if _complete_text(operator, maximum=200) and _complete_text(reviewer, maximum=200):
        if str(operator).strip().casefold() == str(reviewer).strip().casefold():
            blockers.append("evidence.independent_reviewer")
    try:
        rehearsed_at = date.fromisoformat(evidence.get("rehearsal_date"))
        if rehearsed_at > (today or date.today()):
            blockers.append("evidence.rehearsal_date_future")
    except (TypeError, ValueError):
        blockers.append("evidence.rehearsal_date")
    if evidence.get("no_voter_data_attestation") is not True:
        blockers.append("evidence.no_voter_data_attestation")
    if evidence.get("public_search_disabled_attestation") is not True:
        blockers.append("evidence.public_search_disabled_attestation")
    probe = evidence.get("deployment_probe")
    if not (
        isinstance(probe, dict)
        and probe.get("ready") is True
        and probe.get("blockers") == []
        and probe.get("release_commit") == commit
        and isinstance(probe.get("checks_passed"), int)
        and probe.get("checks_passed") == probe.get("checks_total")
        and probe.get("checks_total", 0) >= 42
        and probe.get("values_redacted") is True
    ):
        blockers.append("evidence.deployment_probe_release_binding")

    checks = evidence.get("checks")
    check_by_id = {
        item.get("id"): item
        for item in checks
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(checks, list) else {}
    expected_ids = {identifier for identifier, _label in CHECKS}
    if set(check_by_id) != expected_ids:
        blockers.append("evidence.check_set")
    for identifier, _label in CHECKS:
        item = check_by_id.get(identifier)
        if not item:
            continue
        result = item.get("result")
        if result not in RESULTS:
            blockers.append(f"check.{identifier}.invalid_result")
        elif result == "pass":
            if not _complete_text(item.get("evidence")):
                blockers.append(f"check.{identifier}.missing_evidence")
        elif result == "fail":
            if not _complete_text(item.get("evidence")) or not _complete_text(item.get("remediation")):
                blockers.append(f"check.{identifier}.incomplete_failure")
            if item.get("retest_result") != "pass":
                blockers.append(f"check.{identifier}.retest_not_passed")
        else:
            blockers.append(f"check.{identifier}.not_tested")

    unique_blockers = list(dict.fromkeys(blockers))
    return {
        "ready_for_guidance_rehearsal_signoff": not unique_blockers,
        "blockers": unique_blockers,
        "required_check_count": len(CHECKS),
        "values_redacted": True,
    }


def _safe_output_path(output: Path) -> Path:
    resolved = output.resolve()
    if resolved == ROOT or (ROOT in resolved.parents and not any(
        resolved.is_relative_to((ROOT / directory).resolve()) for directory in ("reports", "data")
    )):
        raise ValueError("repository evidence templates must stay under ignored reports/ or data/")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate guidance-only deployment rehearsal evidence.")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--create-template", action="store_true")
    actions.add_argument("--validate", type=Path, metavar="EVIDENCE")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--require-full-pass", action="store_true")
    args = parser.parse_args(argv)

    if args.create_template:
        if args.output is None:
            parser.error("--output is required with --create-template")
        try:
            output = _safe_output_path(args.output)
            if output.exists() and not args.replace:
                raise ValueError("output already exists; use --replace only after preserving prior evidence")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(create_template(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps({"written": str(args.output), "ready_for_guidance_rehearsal_signoff": False}, sort_keys=True))
        return 0

    if args.output is not None:
        parser.error("--output is only valid with --create-template")
    try:
        payload = _load_json(args.validate)
        report = validate_evidence(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        report = {
            "ready_for_guidance_rehearsal_signoff": False,
            "blockers": ["evidence.unreadable"],
            "required_check_count": len(CHECKS),
            "values_redacted": True,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.require_full_pass and not report["ready_for_guidance_rehearsal_signoff"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
