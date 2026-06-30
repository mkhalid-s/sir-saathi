"""Local readiness report for loaded SIR roll data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from typing import Any, Callable, Protocol

from pipeline.sir_saathi_pipeline.state_registry import StateConfig, load_all_states

DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"
DEFAULT_MAX_QUALITY_ISSUE_RATE = 0.05


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ...) -> Any: ...
    def fetchone(self) -> dict[str, Any] | None: ...
    def fetchall(self) -> list[dict[str, Any]]: ...


class ConnectionLike(Protocol):
    def cursor(self) -> Any: ...


@dataclass(frozen=True)
class ReadinessRequest:
    state_id: str
    ac_number: int
    part_number: int | None = None
    max_quality_issue_rate: float = DEFAULT_MAX_QUALITY_ISSUE_RATE

    def validate(self) -> None:
        if not self.state_id:
            raise ValueError("state_id is required")
        if self.ac_number <= 0:
            raise ValueError("ac_number must be positive")
        if self.part_number is not None and self.part_number <= 0:
            raise ValueError("part_number must be positive")
        if self.max_quality_issue_rate < 0 or self.max_quality_issue_rate > 1:
            raise ValueError("max_quality_issue_rate must be between 0 and 1")


@dataclass(frozen=True)
class LoadedDataSummary:
    source_documents: int
    extraction_runs: int
    validated_runs: int
    nonvalidated_runs: int
    expected_records: int
    parsed_records: int
    voter_records: int
    ok_records: int
    issue_records: int
    quality_issue_rate: float
    quality_summary: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_documents": self.source_documents,
            "extraction_runs": self.extraction_runs,
            "validated_runs": self.validated_runs,
            "nonvalidated_runs": self.nonvalidated_runs,
            "expected_records": self.expected_records,
            "parsed_records": self.parsed_records,
            "voter_records": self.voter_records,
            "ok_records": self.ok_records,
            "issue_records": self.issue_records,
            "quality_issue_rate": round(self.quality_issue_rate, 4),
            "quality_summary": self.quality_summary,
        }


def roll_summary_sql() -> str:
    return """
        SELECT
            COUNT(DISTINCT sd.source_document_id) AS source_documents,
            COUNT(DISTINCT er.extraction_run_id) AS extraction_runs,
            COUNT(DISTINCT er.extraction_run_id) FILTER (WHERE er.status = 'validated') AS validated_runs,
            COUNT(DISTINCT er.extraction_run_id) FILTER (WHERE er.status <> 'validated') AS nonvalidated_runs,
            COALESCE(SUM(er.expected_records), 0) AS expected_records,
            COALESCE(SUM(er.parsed_records), 0) AS parsed_records
        FROM roll_versions rv
        LEFT JOIN source_documents sd ON rv.roll_version_id = sd.roll_version_id
        LEFT JOIN extraction_runs er ON sd.source_document_id = er.source_document_id
        WHERE rv.state_id = %s
    """


def voter_summary_sql(part_number: int | None) -> str:
    part_filter = "AND ps.part_number = %s" if part_number is not None else ""
    return f"""
        SELECT
            COUNT(*) AS voter_records,
            COUNT(*) FILTER (WHERE vr.data_quality = 'ok') AS ok_records,
            COUNT(*) FILTER (WHERE vr.data_quality <> 'ok') AS issue_records
        FROM voter_records vr
        JOIN assembly_constituencies ac ON vr.ac_id = ac.ac_id
        LEFT JOIN polling_stations ps ON vr.polling_station_id = ps.polling_station_id
        WHERE vr.state_id = %s
          AND ac.ac_number = %s
          {part_filter}
    """


def quality_breakdown_sql(part_number: int | None) -> str:
    part_filter = "AND ps.part_number = %s" if part_number is not None else ""
    return f"""
        SELECT vr.data_quality, COUNT(*) AS count
        FROM voter_records vr
        JOIN assembly_constituencies ac ON vr.ac_id = ac.ac_id
        LEFT JOIN polling_stations ps ON vr.polling_station_id = ps.polling_station_id
        WHERE vr.state_id = %s
          AND ac.ac_number = %s
          {part_filter}
        GROUP BY vr.data_quality
        ORDER BY count DESC, vr.data_quality ASC
    """


def fetch_loaded_summary(connection: ConnectionLike, request: ReadinessRequest) -> LoadedDataSummary:
    request.validate()
    voter_params: tuple[Any, ...] = (request.state_id, request.ac_number)
    if request.part_number is not None:
        voter_params = (*voter_params, request.part_number)

    with connection.cursor() as cursor:
        cursor.execute(roll_summary_sql(), (request.state_id,))
        roll_row = cursor.fetchone() or {}
        cursor.execute(voter_summary_sql(request.part_number), voter_params)
        voter_row = cursor.fetchone() or {}
        cursor.execute(quality_breakdown_sql(request.part_number), voter_params)
        quality_rows = cursor.fetchall()

    voter_records = int(voter_row.get("voter_records") or 0)
    issue_records = int(voter_row.get("issue_records") or 0)
    issue_rate = issue_records / voter_records if voter_records else 0.0
    quality_summary = {
        str(row.get("data_quality") or "unknown"): int(row.get("count") or 0)
        for row in quality_rows
    }

    return LoadedDataSummary(
        source_documents=int(roll_row.get("source_documents") or 0),
        extraction_runs=int(roll_row.get("extraction_runs") or 0),
        validated_runs=int(roll_row.get("validated_runs") or 0),
        nonvalidated_runs=int(roll_row.get("nonvalidated_runs") or 0),
        expected_records=int(roll_row.get("expected_records") or 0),
        parsed_records=int(roll_row.get("parsed_records") or 0),
        voter_records=voter_records,
        ok_records=int(voter_row.get("ok_records") or 0),
        issue_records=issue_records,
        quality_issue_rate=issue_rate,
        quality_summary=quality_summary,
    )


def readiness_blockers(request: ReadinessRequest, state: StateConfig, summary: LoadedDataSummary) -> list[str]:
    blockers: list[str] = []
    if not state.public_launch_ready:
        blockers.append("state config is not marked public_launch_ready")
    if state.schedule_provenance.confidence != "official":
        blockers.append("schedule provenance is not official")
    if summary.source_documents == 0:
        blockers.append("no source documents loaded")
    if summary.extraction_runs == 0:
        blockers.append("no extraction runs loaded")
    if summary.nonvalidated_runs > 0:
        blockers.append("one or more extraction runs are not validated")
    if summary.expected_records != summary.parsed_records:
        blockers.append("expected and parsed record counts do not match")
    if summary.voter_records == 0:
        blockers.append("no scoped voter records loaded")
    if summary.quality_issue_rate > request.max_quality_issue_rate:
        blockers.append("data quality issue rate exceeds threshold")
    return blockers


def build_readiness_report(
    request: ReadinessRequest,
    state: StateConfig,
    summary: LoadedDataSummary,
) -> dict[str, Any]:
    blockers = readiness_blockers(request, state, summary)
    return {
        "local_only": True,
        "safe_for_public": False,
        "ready_for_public": not blockers,
        "state_id": request.state_id,
        "ac_number": request.ac_number,
        "part_number": request.part_number,
        "max_quality_issue_rate": request.max_quality_issue_rate,
        "state_config": {
            "data_capability": state.data_capability,
            "public_launch_ready": state.public_launch_ready,
            "parser_status": state.parser_status,
            "schedule_provenance": state.schedule_provenance.confidence,
        },
        "loaded_data": summary.as_dict(),
        "blockers": blockers,
    }


def validate_readiness(
    connection: ConnectionLike,
    request: ReadinessRequest,
    *,
    states: dict[str, StateConfig] | None = None,
) -> dict[str, Any]:
    request.validate()
    state_registry = states or load_all_states()
    if request.state_id not in state_registry:
        raise ValueError(f"unknown state_id: {request.state_id}")
    summary = fetch_loaded_summary(connection, request)
    return build_readiness_report(request, state_registry[request.state_id], summary)


def readiness_database(database_url: str, request: ReadinessRequest) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        return validate_readiness(connection, request)


def failure_report(message: str) -> dict[str, Any]:
    return {
        "local_only": True,
        "safe_for_public": False,
        "ready_for_public": False,
        "error": message,
        "blockers": [message],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report local readiness for loaded SIR roll data.")
    parser.add_argument("--state", required=True, help="Canonical state id, for example IN-MH.")
    parser.add_argument("--ac", required=True, type=int, help="Assembly Constituency number.")
    parser.add_argument("--part", type=int, help="Optional polling part number.")
    parser.add_argument("--max-quality-issue-rate", type=float, default=DEFAULT_MAX_QUALITY_ISSUE_RATE)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    readiness_fn: Callable[[str, ReadinessRequest], dict[str, Any]] = readiness_database,
) -> int:
    args = build_parser().parse_args(argv)
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        print(json.dumps(failure_report(f"{DATABASE_URL_ENV} is required for readiness report"), indent=2, sort_keys=True))
        return 1

    request = ReadinessRequest(
        state_id=args.state,
        ac_number=args.ac,
        part_number=args.part,
        max_quality_issue_rate=args.max_quality_issue_rate,
    )
    try:
        report = readiness_fn(database_url, request)
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
