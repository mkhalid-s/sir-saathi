"""Local-only search validation for loaded roll data."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Protocol

from pipeline.sir_saathi_pipeline.ingestion import normalize_name

DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"
MAX_LOCAL_SEARCH_LIMIT = 20
DEFAULT_SIMILARITY_THRESHOLD = 0.2


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ...) -> Any: ...
    def fetchall(self) -> list[dict[str, Any]]: ...


class ConnectionLike(Protocol):
    def cursor(self) -> Any: ...


@dataclass(frozen=True)
class LocalSearchRequest:
    state_id: str
    ac_number: int
    query: str
    limit: int = 10
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD
    include_epic_last4: bool = False

    @property
    def normalized_query(self) -> str:
        return normalize_name(self.query)

    def validate(self) -> None:
        if not self.state_id:
            raise ValueError("state_id is required")
        if self.ac_number <= 0:
            raise ValueError("ac_number must be positive")
        if len(self.normalized_query) < 2:
            raise ValueError("search query must contain at least two normalized characters")
        if self.limit < 1 or self.limit > MAX_LOCAL_SEARCH_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LOCAL_SEARCH_LIMIT}")
        if self.threshold < 0 or self.threshold > 1:
            raise ValueError("similarity threshold must be between 0 and 1")


@dataclass(frozen=True)
class LocalSearchResult:
    name: str
    age: int | None
    gender: str | None
    relation_type: str | None
    ac_number: int
    part_number: int | None
    serial_number: int | None
    score: float
    data_quality: str
    epic_last4: str | None = None

    def as_dict(self, *, include_epic_last4: bool) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "relation_type": self.relation_type,
            "ac_number": self.ac_number,
            "part_number": self.part_number,
            "serial_number": self.serial_number,
            "score": round(self.score, 4),
            "data_quality": self.data_quality,
        }
        if include_epic_last4:
            payload["epic_last4"] = self.epic_last4
        return payload


def safe_query_summary(query: str) -> str:
    normalized = normalize_name(query)
    if len(normalized) <= 2:
        return "short-query"
    return f"len:{len(normalized)} prefix:{normalized[:2]}"


def local_search_sql() -> str:
    return """
        SELECT
            vr.name_original AS name,
            vr.age,
            vr.gender,
            vr.relation_type,
            ac.ac_number,
            ps.part_number,
            vr.serial_number,
            vr.epic_last4,
            vr.data_quality,
            similarity(vr.name_normalized, %s) AS score
        FROM voter_records vr
        JOIN assembly_constituencies ac ON vr.ac_id = ac.ac_id
        LEFT JOIN polling_stations ps ON vr.polling_station_id = ps.polling_station_id
        WHERE vr.state_id = %s
          AND ac.ac_number = %s
          AND similarity(vr.name_normalized, %s) >= %s
        ORDER BY score DESC, vr.serial_number ASC
        LIMIT %s
    """


def search_loaded_rolls(connection: ConnectionLike, request: LocalSearchRequest) -> list[LocalSearchResult]:
    request.validate()
    normalized_query = request.normalized_query
    with connection.cursor() as cursor:
        cursor.execute(
            local_search_sql(),
            (
                normalized_query,
                request.state_id,
                request.ac_number,
                normalized_query,
                request.threshold,
                request.limit,
            ),
        )
        rows = cursor.fetchall()
    return [
        LocalSearchResult(
            name=str(row["name"]),
            age=row.get("age"),
            gender=row.get("gender"),
            relation_type=row.get("relation_type"),
            ac_number=int(row["ac_number"]),
            part_number=row.get("part_number"),
            serial_number=row.get("serial_number"),
            score=float(row["score"]),
            data_quality=row.get("data_quality") or "ok",
            epic_last4=row.get("epic_last4"),
        )
        for row in rows
    ]


def search_report(
    request: LocalSearchRequest,
    results: list[LocalSearchResult],
    *,
    elapsed_ms: float,
) -> dict[str, Any]:
    return {
        "local_only": True,
        "safe_for_public": False,
        "state_id": request.state_id,
        "ac_number": request.ac_number,
        "query_summary": safe_query_summary(request.query),
        "threshold": request.threshold,
        "limit": request.limit,
        "elapsed_ms": round(elapsed_ms, 2),
        "result_count": len(results),
        "results": [
            result.as_dict(include_epic_last4=request.include_epic_last4)
            for result in results
        ],
    }


def validate_local_search(connection: ConnectionLike, request: LocalSearchRequest) -> dict[str, Any]:
    started = time.perf_counter()
    results = search_loaded_rolls(connection, request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return search_report(request, results, elapsed_ms=elapsed_ms)


def search_database(database_url: str, request: LocalSearchRequest) -> dict[str, Any]:
    import psycopg
    from psycopg.rows import dict_row

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        return validate_local_search(connection, request)


def failure_report(message: str) -> dict[str, Any]:
    return {
        "local_only": True,
        "safe_for_public": False,
        "error": message,
        "result_count": 0,
        "results": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate local loaded-roll search without public API exposure.")
    parser.add_argument("--state", required=True, help="Canonical state id, for example IN-MH.")
    parser.add_argument("--ac", required=True, type=int, help="Assembly Constituency number.")
    parser.add_argument("--name", required=True, help="Name query used only for local validation.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--threshold", type=float, default=DEFAULT_SIMILARITY_THRESHOLD)
    parser.add_argument("--include-epic-last4", action="store_true")
    return parser


def main(
    argv: list[str] | None = None,
    *,
    search_fn: Callable[[str, LocalSearchRequest], dict[str, Any]] = search_database,
) -> int:
    args = build_parser().parse_args(argv)
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        print(json.dumps(failure_report(f"{DATABASE_URL_ENV} is required for local search validation"), indent=2, sort_keys=True))
        return 1

    request = LocalSearchRequest(
        state_id=args.state,
        ac_number=args.ac,
        query=args.name,
        limit=args.limit,
        threshold=args.threshold,
        include_epic_last4=args.include_epic_last4,
    )
    try:
        report = search_fn(database_url, request)
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
