"""DB-ready ingestion mapping for parsed electoral roll payloads.

This module is intentionally local-only: it prepares rows for the existing
PostgreSQL schema but does not download PDFs, write raw exports, or connect to
the database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import re
from typing import Any


@dataclass(frozen=True)
class SourceDocumentInput:
    state_id: str
    source_uri: str
    checksum: str
    parser_hint: str
    local_path: str | None = None


@dataclass(frozen=True)
class ParsedRollInput:
    state_id: str
    roll_year: int
    roll_kind: str
    language: str
    source_label: str
    parser_name: str
    metadata: dict[str, Any]
    voters: tuple[dict[str, Any], ...]
    source_document: SourceDocumentInput
    source_url: str | None = None


@dataclass(frozen=True)
class IngestionBatch:
    source_document: dict[str, Any]
    roll_version: dict[str, Any]
    assembly_constituency: dict[str, Any]
    polling_station: dict[str, Any]
    extraction_run: dict[str, Any]
    voter_records: tuple[dict[str, Any], ...]


def stable_id(prefix: str, *parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}_{digest}"


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().casefold())


def epic_fingerprint(epic_value: str | None, *, hash_salt: str) -> tuple[str | None, str | None]:
    if not epic_value:
        return None, None
    normalized = re.sub(r"\s+", "", epic_value.strip().upper())
    digest = hashlib.sha256(f"{hash_salt}:{normalized}".encode("utf-8")).hexdigest()
    return digest, normalized[-4:]


def validate_parsed_roll(parsed_roll: ParsedRollInput) -> None:
    expected_records = int(parsed_roll.metadata.get("total_voters") or len(parsed_roll.voters))
    parsed_records = len(parsed_roll.voters)
    if expected_records != parsed_records:
        raise ValueError(f"parsed record count mismatch: expected {expected_records}, got {parsed_records}")
    if not parsed_roll.source_document.checksum:
        raise ValueError("source document checksum is required before ingestion")
    if not parsed_roll.source_document.source_uri:
        raise ValueError("source document URI is required before ingestion")


def quality_summary(voters: tuple[dict[str, Any], ...]) -> dict[str, int]:
    issue_counts: dict[str, int] = {}
    for voter in voters:
        for issue in str(voter.get("data_quality") or "ok").split(","):
            cleaned = issue.strip() or "ok"
            issue_counts[cleaned] = issue_counts.get(cleaned, 0) + 1
    return issue_counts


def build_ingestion_batch(parsed_roll: ParsedRollInput, *, hash_salt: str) -> IngestionBatch:
    validate_parsed_roll(parsed_roll)

    metadata = parsed_roll.metadata
    ac_number = int(metadata["ac_number"])
    part_number = int(metadata["part_number"])
    roll_version_id = stable_id(
        "roll",
        parsed_roll.state_id,
        parsed_roll.roll_year,
        parsed_roll.roll_kind,
        parsed_roll.language,
        ac_number,
        part_number,
    )
    source_document_id = stable_id("srcdoc", parsed_roll.state_id, parsed_roll.source_document.checksum)
    ac_id = stable_id("ac", parsed_roll.state_id, ac_number)
    polling_station_id = stable_id("ps", parsed_roll.state_id, ac_number, part_number)
    extraction_run_id = stable_id("extract", source_document_id, parsed_roll.parser_name, len(parsed_roll.voters))

    source_document = {
        "source_document_id": source_document_id,
        "state_id": parsed_roll.state_id,
        "roll_version_id": roll_version_id,
        "source_uri": parsed_roll.source_document.source_uri,
        "local_path": parsed_roll.source_document.local_path,
        "checksum": parsed_roll.source_document.checksum,
        "parser_hint": parsed_roll.source_document.parser_hint,
        "status": "registered",
    }
    roll_version = {
        "roll_version_id": roll_version_id,
        "state_id": parsed_roll.state_id,
        "roll_year": parsed_roll.roll_year,
        "roll_kind": parsed_roll.roll_kind,
        "language": parsed_roll.language,
        "source_label": parsed_roll.source_label,
        "source_url": parsed_roll.source_url,
    }
    assembly_constituency = {
        "ac_id": ac_id,
        "state_id": parsed_roll.state_id,
        "district_id": None,
        "ac_number": ac_number,
        "name": str(metadata.get("ac_name_encoded") or f"AC {ac_number}"),
        "reservation_status": metadata.get("ac_reservation_encoded") or None,
    }
    polling_station = {
        "polling_station_id": polling_station_id,
        "ac_id": ac_id,
        "part_number": part_number,
        "name": metadata.get("polling_station_name_encoded") or None,
        "address_redacted": None,
        "source_updated_at": None,
    }
    extraction_run = {
        "extraction_run_id": extraction_run_id,
        "source_document_id": source_document_id,
        "parser_name": parsed_roll.parser_name,
        "expected_records": int(metadata.get("total_voters") or len(parsed_roll.voters)),
        "parsed_records": len(parsed_roll.voters),
        "quality_summary": quality_summary(parsed_roll.voters),
        "status": "validated",
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }

    voter_rows = []
    for voter in parsed_roll.voters:
        serial_number = int(voter["serial_number"])
        voter_name = str(voter.get("voter_name") or "")
        relative_name = str(voter.get("relative_name") or "")
        epic_hash, epic_last4 = epic_fingerprint(voter.get("epic_number"), hash_salt=hash_salt)
        voter_rows.append(
            {
                "voter_record_id": stable_id("voter", roll_version_id, ac_number, part_number, serial_number),
                "roll_version_id": roll_version_id,
                "state_id": parsed_roll.state_id,
                "ac_id": ac_id,
                "polling_station_id": polling_station_id,
                "serial_number": serial_number,
                "name_original": voter_name,
                "name_normalized": normalize_name(voter_name),
                "name_phonetic": None,
                "relation_type": voter.get("relation_type") or None,
                "relative_name_normalized": normalize_name(relative_name),
                "age": voter.get("age"),
                "gender": voter.get("gender") or None,
                "epic_hash": epic_hash,
                "epic_last4": epic_last4,
                "data_quality": voter.get("data_quality") or "ok",
                "source_confidence": 1.0,
            }
        )

    return IngestionBatch(
        source_document=source_document,
        roll_version=roll_version,
        assembly_constituency=assembly_constituency,
        polling_station=polling_station,
        extraction_run=extraction_run,
        voter_records=tuple(voter_rows),
    )
