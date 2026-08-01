"""Bounded PostgreSQL search behind reviewed roll/geography allowlists."""

from __future__ import annotations

import os
from typing import Any, Callable, Protocol

from .models import InternalVoterRecord
from .search import SearchRequest, validate_search_scope

DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"
PUBLIC_SIMILARITY_THRESHOLD = 0.2
PUBLIC_SEARCH_STATEMENT_TIMEOUT_MS = 3_000


class SearchBackend(Protocol):
    def search(self, request: SearchRequest) -> list[InternalVoterRecord]: ...


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...]) -> Any: ...
    def fetchall(self) -> list[dict[str, Any]]: ...


class ConnectionLike(Protocol):
    def cursor(self) -> Any: ...
    def close(self) -> None: ...


ConnectionFactory = Callable[[], ConnectionLike]


def public_search_sql() -> str:
    return """
        WITH search_input AS (SELECT %s::text AS query)
        SELECT
            vr.state_id,
            ac.ac_number,
            ps.part_number,
            vr.serial_number,
            vr.name_original AS name,
            rv.roll_year,
            rv.roll_kind,
            vr.data_quality,
            rv.source_label,
            vr.epic_last4,
            GREATEST(
                similarity(vr.name_normalized, search_input.query),
                similarity(COALESCE(vr.name_phonetic, ''), search_input.query)
            ) AS confidence
        FROM voter_records vr
        CROSS JOIN search_input
        JOIN roll_versions rv ON vr.roll_version_id = rv.roll_version_id
        JOIN assembly_constituencies ac ON vr.ac_id = ac.ac_id
        LEFT JOIN polling_stations ps ON vr.polling_station_id = ps.polling_station_id
        JOIN public_search_scopes scope
          ON scope.roll_version_id = vr.roll_version_id
         AND scope.ac_id = vr.ac_id
         AND scope.enabled = TRUE
        WHERE vr.state_id = %s
          AND ac.ac_number = %s
          AND (%s::integer IS NULL OR ps.part_number = %s)
          AND GREATEST(
                similarity(vr.name_normalized, search_input.query),
                similarity(COALESCE(vr.name_phonetic, ''), search_input.query)
          ) >= %s
        ORDER BY confidence DESC, vr.serial_number ASC
        LIMIT %s
    """


class PostgresSearchBackend:
    def __init__(self, connection_factory: ConnectionFactory) -> None:
        self._connection_factory = connection_factory

    def search(self, request: SearchRequest) -> list[InternalVoterRecord]:
        from pipeline.sir_saathi_pipeline.ingestion import normalize_name

        validate_search_scope(request)
        connection = self._connection_factory()
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY", ())
                cursor.execute(
                    f"SET LOCAL statement_timeout = '{PUBLIC_SEARCH_STATEMENT_TIMEOUT_MS}ms'",
                    (),
                )
                cursor.execute(
                    public_search_sql(),
                    (
                        normalize_name(request.query),
                        request.state_id,
                        request.ac_number,
                        request.part_number,
                        request.part_number,
                        PUBLIC_SIMILARITY_THRESHOLD,
                        request.limit,
                    ),
                )
                rows = cursor.fetchall()
        finally:
            connection.close()
        return [
            InternalVoterRecord(
                state_id=str(row["state_id"]),
                ac_number=int(row["ac_number"]),
                part_number=row.get("part_number"),
                serial_number=row.get("serial_number"),
                name=str(row["name"]),
                roll_year=int(row["roll_year"]),
                roll_kind=str(row["roll_kind"]),
                data_quality=str(row.get("data_quality") or "ok"),
                source_label=str(row["source_label"]),
                confidence=float(row["confidence"]),
                epic_last4=row.get("epic_last4"),
            )
            for row in rows
        ]

    def ready(self) -> bool:
        """Check connectivity without reading voter or scope data."""

        try:
            connection = self._connection_factory()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1", ())
            finally:
                connection.close()
        except Exception:
            return False
        return True


def configured_search_backend() -> SearchBackend | None:
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        return None

    def connect() -> ConnectionLike:
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            database_url,
            row_factory=dict_row,
            connect_timeout=3,
            options=(
                f"-c statement_timeout={PUBLIC_SEARCH_STATEMENT_TIMEOUT_MS} "
                "-c default_transaction_read_only=on"
            ),
        )

    return PostgresSearchBackend(connect)
