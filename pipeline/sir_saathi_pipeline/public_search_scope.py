"""Dry-run-first, audited management of exact public-search scopes."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Protocol
from uuid import uuid4

from .readiness_report import DEFAULT_MAX_QUALITY_ISSUE_RATE
from .state_registry import StateConfig, load_all_states

DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ...) -> Any: ...
    def fetchone(self) -> dict[str, Any] | None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> Any: ...
    def transaction(self) -> Any: ...


@dataclass(frozen=True)
class ScopeRequest:
    state_id: str
    ac_number: int
    roll_version_id: str
    ac_id: str
    max_quality_issue_rate: float = DEFAULT_MAX_QUALITY_ISSUE_RATE

    def validate(self) -> None:
        if not self.state_id.strip():
            raise ValueError("state_id is required")
        if self.ac_number <= 0:
            raise ValueError("ac_number must be positive")
        if not self.roll_version_id.strip():
            raise ValueError("roll_version_id is required")
        if not self.ac_id.strip():
            raise ValueError("ac_id is required")
        if not 0 <= self.max_quality_issue_rate <= 1:
            raise ValueError("max_quality_issue_rate must be between 0 and 1")


def exact_scope_sql() -> str:
    return """
        WITH source_summary AS (
            SELECT
                COUNT(DISTINCT sd.source_document_id) AS source_documents,
                COUNT(DISTINCT er.extraction_run_id) AS extraction_runs,
                COUNT(DISTINCT er.extraction_run_id) FILTER (WHERE er.status = 'validated') AS validated_runs,
                COUNT(DISTINCT er.extraction_run_id) FILTER (WHERE er.status <> 'validated') AS nonvalidated_runs,
                COALESCE(SUM(er.expected_records), 0) AS expected_records,
                COALESCE(SUM(er.parsed_records), 0) AS parsed_records
            FROM source_documents sd
            LEFT JOIN extraction_runs er ON er.source_document_id = sd.source_document_id
            WHERE sd.roll_version_id = %s
        ),
        voter_summary AS (
            SELECT
                COUNT(*) AS voter_records,
                COUNT(*) FILTER (WHERE data_quality = 'ok') AS ok_records,
                COUNT(*) FILTER (WHERE data_quality <> 'ok') AS issue_records
            FROM voter_records
            WHERE roll_version_id = %s
              AND ac_id = %s
              AND state_id = %s
        )
        SELECT
            rv.roll_version_id,
            rv.state_id,
            rv.roll_year,
            rv.roll_kind,
            ac.ac_id,
            ac.ac_number,
            ac.geography_version,
            ss.source_documents,
            ss.extraction_runs,
            ss.validated_runs,
            ss.nonvalidated_runs,
            ss.expected_records,
            ss.parsed_records,
            vs.voter_records,
            vs.ok_records,
            vs.issue_records,
            scope.enabled AS currently_enabled,
            scope.operated_by,
            scope.reviewed_by,
            scope.reviewed_at
        FROM roll_versions rv
        JOIN assembly_constituencies ac
          ON ac.ac_id = %s
         AND ac.state_id = rv.state_id
        CROSS JOIN source_summary ss
        CROSS JOIN voter_summary vs
        LEFT JOIN public_search_scopes scope
          ON scope.roll_version_id = rv.roll_version_id
         AND scope.ac_id = ac.ac_id
        WHERE rv.roll_version_id = %s
          AND rv.state_id = %s
          AND ac.ac_number = %s
    """


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def inspect_scope(
    connection: ConnectionLike,
    request: ScopeRequest,
    *,
    states: dict[str, StateConfig] | None = None,
) -> dict[str, Any]:
    request.validate()
    registry = states or load_all_states()
    state = registry.get(request.state_id)
    if state is None:
        raise ValueError(f"unknown state_id: {request.state_id}")

    with connection.cursor() as cursor:
        return _inspect_scope_with_cursor(cursor, request, state)


def _inspect_scope_with_cursor(
    cursor: CursorLike,
    request: ScopeRequest,
    state: StateConfig,
) -> dict[str, Any]:
    cursor.execute(
        exact_scope_sql(),
        (
            request.roll_version_id,
            request.roll_version_id,
            request.ac_id,
            request.state_id,
            request.ac_id,
            request.roll_version_id,
            request.state_id,
            request.ac_number,
        ),
    )
    row = cursor.fetchone()

    blockers: list[str] = []
    if not state.public_launch_ready:
        blockers.append("state config is not marked public_launch_ready")
    if not state.is_search_enabled:
        blockers.append("state config does not permit indexed search")
    if state.schedule_provenance.confidence != "official":
        blockers.append("schedule provenance is not official")
    if row is None:
        blockers.append("exact roll version and versioned AC scope does not exist")
        loaded = None
        scope = {"currently_enabled": False, "operated_by": None, "reviewed_by": None, "reviewed_at": None}
    else:
        voter_records = int(row.get("voter_records") or 0)
        issue_records = int(row.get("issue_records") or 0)
        issue_rate = issue_records / voter_records if voter_records else 0.0
        source_documents = int(row.get("source_documents") or 0)
        extraction_runs = int(row.get("extraction_runs") or 0)
        nonvalidated_runs = int(row.get("nonvalidated_runs") or 0)
        expected_records = int(row.get("expected_records") or 0)
        parsed_records = int(row.get("parsed_records") or 0)
        if source_documents == 0:
            blockers.append("no source documents loaded for exact roll version")
        if extraction_runs == 0:
            blockers.append("no extraction runs loaded for exact roll version")
        if nonvalidated_runs > 0:
            blockers.append("one or more extraction runs are not validated")
        if expected_records != parsed_records:
            blockers.append("expected and parsed record counts do not match")
        if voter_records == 0:
            blockers.append("no voter records loaded for exact roll and AC scope")
        if issue_rate > request.max_quality_issue_rate:
            blockers.append("data quality issue rate exceeds threshold")
        loaded = {
            "roll_year": int(row["roll_year"]),
            "roll_kind": str(row["roll_kind"]),
            "geography_version": str(row["geography_version"]),
            "source_documents": source_documents,
            "extraction_runs": extraction_runs,
            "validated_runs": int(row.get("validated_runs") or 0),
            "nonvalidated_runs": nonvalidated_runs,
            "expected_records": expected_records,
            "parsed_records": parsed_records,
            "voter_records": voter_records,
            "ok_records": int(row.get("ok_records") or 0),
            "issue_records": issue_records,
            "quality_issue_rate": round(issue_rate, 4),
        }
        scope = {
            "currently_enabled": bool(row.get("currently_enabled")),
            "operated_by": row.get("operated_by"),
            "reviewed_by": row.get("reviewed_by"),
            "reviewed_at": _json_value(row.get("reviewed_at")),
        }

    return {
        "safe_aggregate_report": True,
        "ready_to_enable": not blockers,
        "state_id": request.state_id,
        "ac_number": request.ac_number,
        "roll_version_id": request.roll_version_id,
        "ac_id": request.ac_id,
        "max_quality_issue_rate": request.max_quality_issue_rate,
        "state_config": {
            "data_capability": state.data_capability,
            "public_launch_ready": state.public_launch_ready,
            "schedule_provenance": state.schedule_provenance.confidence,
        },
        "loaded_data": loaded,
        "authorization": scope,
        "blockers": blockers,
    }


def authorization_sql() -> str:
    return """
        WITH audit AS (
            INSERT INTO public_search_scope_events (
                event_id, roll_version_id, ac_id, action, operated_by, reviewed_by, reason, readiness_snapshot
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            RETURNING reviewed_at
        )
        INSERT INTO public_search_scopes (roll_version_id, ac_id, enabled, operated_by, reviewed_by, reviewed_at)
        SELECT %s, %s, %s, %s, %s, audit.reviewed_at FROM audit
        ON CONFLICT (roll_version_id, ac_id) DO UPDATE SET
            enabled = EXCLUDED.enabled,
            operated_by = EXCLUDED.operated_by,
            reviewed_by = EXCLUDED.reviewed_by,
            reviewed_at = EXCLUDED.reviewed_at
        RETURNING enabled, operated_by, reviewed_by, reviewed_at
    """


def change_authorization(
    connection: ConnectionLike,
    request: ScopeRequest,
    *,
    action: str,
    operated_by: str,
    reviewed_by: str,
    reason: str,
    apply: bool,
    states: dict[str, StateConfig] | None = None,
) -> dict[str, Any]:
    if action not in {"enable", "disable"}:
        raise ValueError("action must be enable or disable")
    if not operated_by.strip():
        raise ValueError("operated_by is required")
    if len(operated_by) > 200:
        raise ValueError("operated_by must be 200 characters or fewer")
    if not reviewed_by.strip():
        raise ValueError("reviewed_by is required")
    if len(reviewed_by) > 200:
        raise ValueError("reviewed_by must be 200 characters or fewer")
    if not reason.strip():
        raise ValueError("reason is required")
    if len(reason) > 500:
        raise ValueError("reason must be 500 characters or fewer")
    if action == "enable" and operated_by.strip().casefold() == reviewed_by.strip().casefold():
        raise ValueError("enable requires different operated_by and reviewed_by identities")

    if not apply:
        report = inspect_scope(connection, request, states=states)
        return {**report, "requested_action": action, "applied": False, "dry_run": True}

    request.validate()
    registry = states or load_all_states()
    state = registry.get(request.state_id)
    if state is None:
        raise ValueError(f"unknown state_id: {request.state_id}")

    with connection.transaction():
        with connection.cursor() as cursor:
            # The evidence check and authorization write must observe one stable
            # database snapshot. A concurrent ingestion change aborts one writer.
            cursor.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            report = _inspect_scope_with_cursor(cursor, request, state)
            if report["loaded_data"] is None:
                return {**report, "requested_action": action, "applied": False}
            if action == "enable" and report["blockers"]:
                return {**report, "requested_action": action, "applied": False}

            event_id = f"scope-event-{uuid4()}"
            evidence = json.dumps(report, sort_keys=True)
            cursor.execute(
                authorization_sql(),
                (
                    event_id,
                    request.roll_version_id,
                    request.ac_id,
                    action,
                    operated_by.strip(),
                    reviewed_by.strip(),
                    reason.strip(),
                    evidence,
                    request.roll_version_id,
                    request.ac_id,
                    action == "enable",
                    operated_by.strip(),
                    reviewed_by.strip(),
                ),
            )
            changed = cursor.fetchone() or {}
    return {
        **report,
        "requested_action": action,
        "applied": True,
        "dry_run": False,
        "event_id": event_id,
        "authorization": {
            "currently_enabled": bool(changed.get("enabled")),
            "operated_by": changed.get("operated_by"),
            "reviewed_by": changed.get("reviewed_by"),
            "reviewed_at": _json_value(changed.get("reviewed_at")),
        },
    }


def scope_database(
    database_url: str,
    request: ScopeRequest,
    *,
    action: str | None,
    operated_by: str | None,
    reviewed_by: str | None,
    reason: str | None,
    apply: bool,
) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        if action is None:
            return inspect_scope(connection, request)
        return change_authorization(
            connection,
            request,
            action=action,
            operated_by=operated_by or "",
            reviewed_by=reviewed_by or "",
            reason=reason or "",
            apply=apply,
        )


def failure_report(message: str) -> dict[str, Any]:
    return {"safe_aggregate_report": True, "ready_to_enable": False, "applied": False, "error": message, "blockers": [message]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect or explicitly change one exact public-search scope.")
    parser.add_argument("--state", required=True)
    parser.add_argument("--ac", required=True, type=int)
    parser.add_argument("--roll-version-id", required=True)
    parser.add_argument("--ac-id", required=True)
    parser.add_argument("--max-quality-issue-rate", type=float, default=DEFAULT_MAX_QUALITY_ISSUE_RATE)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--enable", action="store_const", const="enable", dest="action")
    actions.add_argument("--disable", action="store_const", const="disable", dest="action")
    parser.add_argument("--operated-by", help="Accountable change operator identifier; required for changes.")
    parser.add_argument("--reviewed-by", help="Accountable human reviewer identifier; required for changes.")
    parser.add_argument("--reason", help="Non-empty review/revocation rationale; required for changes.")
    parser.add_argument("--apply", action="store_true", help="Apply the requested change; omission is a dry run.")
    return parser


ScopeFn = Callable[..., dict[str, Any]]


def main(argv: list[str] | None = None, *, scope_fn: ScopeFn = scope_database) -> int:
    args = build_parser().parse_args(argv)
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        print(json.dumps(failure_report(f"{DATABASE_URL_ENV} is required"), indent=2, sort_keys=True))
        return 1
    if args.apply and args.action is None:
        print(json.dumps(failure_report("--apply requires --enable or --disable"), indent=2, sort_keys=True))
        return 1
    if args.action is not None and (not args.operated_by or not args.reviewed_by or not args.reason):
        print(json.dumps(failure_report("changes require --operated-by, --reviewed-by, and --reason"), indent=2, sort_keys=True))
        return 1
    request = ScopeRequest(args.state, args.ac, args.roll_version_id, args.ac_id, args.max_quality_issue_rate)
    try:
        report = scope_fn(
            database_url,
            request,
            action=args.action,
            operated_by=args.operated_by,
            reviewed_by=args.reviewed_by,
            reason=args.reason,
            apply=args.apply,
        )
    except Exception as exc:
        report = failure_report(str(exc))
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.action == "enable" and report.get("blockers"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
