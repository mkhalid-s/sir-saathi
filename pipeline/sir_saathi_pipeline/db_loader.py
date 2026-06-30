"""Local Postgres loader for validated ingestion batches."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Protocol

from pipeline.sir_saathi_pipeline.ingestion import IngestionBatch


class CursorLike(Protocol):
    def execute(self, query: str, params: tuple[Any, ...] = ...) -> Any: ...
    def fetchone(self) -> tuple[Any, ...] | None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> Any: ...
    def transaction(self) -> Any: ...


class MissingStateError(ValueError):
    """Raised when a load targets a state that is not in the canonical states table."""


@dataclass(frozen=True)
class LoadSummary:
    loaded: bool
    state_id: str
    source_checksum: str | None
    expected_records: int | None
    parsed_records: int | None
    row_counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "state_id": self.state_id,
            "source_checksum": self.source_checksum,
            "expected_records": self.expected_records,
            "parsed_records": self.parsed_records,
            "row_counts": self.row_counts,
        }


def _execute(cursor: CursorLike, query: str, params: tuple[Any, ...]) -> None:
    cursor.execute(query, params)


def require_state_exists(cursor: CursorLike, state_id: str) -> None:
    cursor.execute("SELECT 1 FROM states WHERE state_id = %s", (state_id,))
    if cursor.fetchone() is None:
        raise MissingStateError(f"state row must exist before loading rolls: {state_id}")


def load_ingestion_batch(connection: ConnectionLike, batch: IngestionBatch) -> LoadSummary:
    """Load an ingestion batch transactionally with idempotent upserts."""

    row_counts = {
        "assembly_constituencies": 0,
        "polling_stations": 0,
        "roll_versions": 0,
        "source_documents": 0,
        "extraction_runs": 0,
        "voter_records": 0,
    }
    with connection.transaction():
        with connection.cursor() as cursor:
            require_state_exists(cursor, batch.roll_version["state_id"])
            _execute(
                cursor,
                """
                INSERT INTO assembly_constituencies (
                    ac_id, state_id, district_id, ac_number, name, reservation_status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (ac_id) DO UPDATE SET
                    state_id = EXCLUDED.state_id,
                    district_id = EXCLUDED.district_id,
                    ac_number = EXCLUDED.ac_number,
                    name = EXCLUDED.name,
                    reservation_status = EXCLUDED.reservation_status
                """,
                (
                    batch.assembly_constituency["ac_id"],
                    batch.assembly_constituency["state_id"],
                    batch.assembly_constituency["district_id"],
                    batch.assembly_constituency["ac_number"],
                    batch.assembly_constituency["name"],
                    batch.assembly_constituency["reservation_status"],
                ),
            )
            row_counts["assembly_constituencies"] = 1

            _execute(
                cursor,
                """
                INSERT INTO polling_stations (
                    polling_station_id, ac_id, part_number, name, address_redacted, source_updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (polling_station_id) DO UPDATE SET
                    ac_id = EXCLUDED.ac_id,
                    part_number = EXCLUDED.part_number,
                    name = EXCLUDED.name,
                    address_redacted = EXCLUDED.address_redacted,
                    source_updated_at = EXCLUDED.source_updated_at
                """,
                (
                    batch.polling_station["polling_station_id"],
                    batch.polling_station["ac_id"],
                    batch.polling_station["part_number"],
                    batch.polling_station["name"],
                    batch.polling_station["address_redacted"],
                    batch.polling_station["source_updated_at"],
                ),
            )
            row_counts["polling_stations"] = 1

            _execute(
                cursor,
                """
                INSERT INTO roll_versions (
                    roll_version_id, state_id, roll_year, roll_kind, language, source_label, source_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (roll_version_id) DO UPDATE SET
                    state_id = EXCLUDED.state_id,
                    roll_year = EXCLUDED.roll_year,
                    roll_kind = EXCLUDED.roll_kind,
                    language = EXCLUDED.language,
                    source_label = EXCLUDED.source_label,
                    source_url = EXCLUDED.source_url
                """,
                (
                    batch.roll_version["roll_version_id"],
                    batch.roll_version["state_id"],
                    batch.roll_version["roll_year"],
                    batch.roll_version["roll_kind"],
                    batch.roll_version["language"],
                    batch.roll_version["source_label"],
                    batch.roll_version["source_url"],
                ),
            )
            row_counts["roll_versions"] = 1

            _execute(
                cursor,
                """
                INSERT INTO source_documents (
                    source_document_id, state_id, roll_version_id, source_uri,
                    local_path, checksum, parser_hint, status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_document_id) DO UPDATE SET
                    state_id = EXCLUDED.state_id,
                    roll_version_id = EXCLUDED.roll_version_id,
                    source_uri = EXCLUDED.source_uri,
                    local_path = EXCLUDED.local_path,
                    checksum = EXCLUDED.checksum,
                    parser_hint = EXCLUDED.parser_hint,
                    status = EXCLUDED.status
                """,
                (
                    batch.source_document["source_document_id"],
                    batch.source_document["state_id"],
                    batch.source_document["roll_version_id"],
                    batch.source_document["source_uri"],
                    batch.source_document["local_path"],
                    batch.source_document["checksum"],
                    batch.source_document["parser_hint"],
                    batch.source_document["status"],
                ),
            )
            row_counts["source_documents"] = 1

            _execute(
                cursor,
                """
                INSERT INTO extraction_runs (
                    extraction_run_id, source_document_id, parser_name, expected_records,
                    parsed_records, quality_summary, status, finished_at
                ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (extraction_run_id) DO UPDATE SET
                    source_document_id = EXCLUDED.source_document_id,
                    parser_name = EXCLUDED.parser_name,
                    expected_records = EXCLUDED.expected_records,
                    parsed_records = EXCLUDED.parsed_records,
                    quality_summary = EXCLUDED.quality_summary,
                    status = EXCLUDED.status,
                    finished_at = EXCLUDED.finished_at
                """,
                (
                    batch.extraction_run["extraction_run_id"],
                    batch.extraction_run["source_document_id"],
                    batch.extraction_run["parser_name"],
                    batch.extraction_run["expected_records"],
                    batch.extraction_run["parsed_records"],
                    json.dumps(batch.extraction_run["quality_summary"], sort_keys=True),
                    batch.extraction_run["status"],
                    batch.extraction_run["finished_at"],
                ),
            )
            row_counts["extraction_runs"] = 1

            for voter in batch.voter_records:
                _execute(
                    cursor,
                    """
                    INSERT INTO voter_records (
                        voter_record_id, roll_version_id, state_id, ac_id, polling_station_id,
                        serial_number, name_original, name_normalized, name_phonetic,
                        relation_type, relative_name_normalized, age, gender, epic_hash,
                        epic_last4, data_quality, source_confidence
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (voter_record_id) DO UPDATE SET
                        roll_version_id = EXCLUDED.roll_version_id,
                        state_id = EXCLUDED.state_id,
                        ac_id = EXCLUDED.ac_id,
                        polling_station_id = EXCLUDED.polling_station_id,
                        serial_number = EXCLUDED.serial_number,
                        name_original = EXCLUDED.name_original,
                        name_normalized = EXCLUDED.name_normalized,
                        name_phonetic = EXCLUDED.name_phonetic,
                        relation_type = EXCLUDED.relation_type,
                        relative_name_normalized = EXCLUDED.relative_name_normalized,
                        age = EXCLUDED.age,
                        gender = EXCLUDED.gender,
                        epic_hash = EXCLUDED.epic_hash,
                        epic_last4 = EXCLUDED.epic_last4,
                        data_quality = EXCLUDED.data_quality,
                        source_confidence = EXCLUDED.source_confidence
                    """,
                    (
                        voter["voter_record_id"],
                        voter["roll_version_id"],
                        voter["state_id"],
                        voter["ac_id"],
                        voter["polling_station_id"],
                        voter["serial_number"],
                        voter["name_original"],
                        voter["name_normalized"],
                        voter["name_phonetic"],
                        voter["relation_type"],
                        voter["relative_name_normalized"],
                        voter["age"],
                        voter["gender"],
                        voter["epic_hash"],
                        voter["epic_last4"],
                        voter["data_quality"],
                        voter["source_confidence"],
                    ),
                )
            row_counts["voter_records"] = len(batch.voter_records)

    return LoadSummary(
        loaded=True,
        state_id=batch.roll_version["state_id"],
        source_checksum=batch.source_document["checksum"],
        expected_records=batch.extraction_run["expected_records"],
        parsed_records=batch.extraction_run["parsed_records"],
        row_counts=row_counts,
    )


def load_batch_to_database(database_url: str, batch: IngestionBatch) -> LoadSummary:
    """Open a local Postgres connection and load a validated batch."""

    import psycopg

    with psycopg.connect(database_url) as connection:
        return load_ingestion_batch(connection, batch)
