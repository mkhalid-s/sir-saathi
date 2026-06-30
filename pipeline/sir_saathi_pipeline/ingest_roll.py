"""Local dry-run CLI for staging parsed roll PDFs.

The command validates a local PDF-to-ingestion path without writing exports,
connecting to Postgres, or enabling public search.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable

from pipeline.parse_2002 import parse_pdf
from pipeline.sir_saathi_pipeline.ingestion import (
    IngestionBatch,
    ParsedRollInput,
    SourceDocumentInput,
    build_ingestion_batch,
)

EPIC_HASH_SALT_ENV = "SIR_SAATHI_EPIC_HASH_SALT"
DEFAULT_LANGUAGE = "mr"
DEFAULT_PARSER_NAME = "parse_2002"
DEFAULT_ROLL_KIND = "historical_base_roll"

ParserFn = Callable[[Path], tuple[dict[str, Any], list[dict[str, Any]], list[str]]]


def compute_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def local_source_uri(path: Path) -> str:
    return f"local://{path.as_posix()}"


def parsed_roll_from_pdf(
    pdf_path: Path,
    *,
    state_id: str,
    roll_year: int | None,
    roll_kind: str,
    language: str,
    source_label: str,
    source_url: str | None,
    parser_fn: ParserFn = parse_pdf,
) -> ParsedRollInput:
    metadata, voters, failures = parser_fn(pdf_path)
    if failures:
        raise ValueError(f"parser reported {len(failures)} failure(s)")

    inferred_year = roll_year or int(metadata.get("revision_year") or 0)
    if inferred_year <= 0:
        raise ValueError("roll year is required when parser metadata does not include revision_year")

    return ParsedRollInput(
        state_id=state_id,
        roll_year=inferred_year,
        roll_kind=roll_kind,
        language=language,
        source_label=source_label,
        parser_name=DEFAULT_PARSER_NAME,
        metadata=metadata,
        voters=tuple(voters),
        source_url=source_url,
        source_document=SourceDocumentInput(
            state_id=state_id,
            source_uri=local_source_uri(pdf_path),
            local_path=str(pdf_path),
            checksum=compute_sha256(pdf_path),
            parser_hint=DEFAULT_PARSER_NAME,
        ),
    )


def safe_report(batch: IngestionBatch) -> dict[str, Any]:
    return {
        "dry_run": True,
        "safe_to_load": True,
        "source_checksum": batch.source_document["checksum"],
        "state_id": batch.roll_version["state_id"],
        "roll_year": batch.roll_version["roll_year"],
        "roll_kind": batch.roll_version["roll_kind"],
        "language": batch.roll_version["language"],
        "ac_number": batch.assembly_constituency["ac_number"],
        "part_number": batch.polling_station["part_number"],
        "expected_records": batch.extraction_run["expected_records"],
        "parsed_records": batch.extraction_run["parsed_records"],
        "quality_summary": batch.extraction_run["quality_summary"],
        "row_counts": {
            "source_documents": 1,
            "roll_versions": 1,
            "assembly_constituencies": 1,
            "polling_stations": 1,
            "extraction_runs": 1,
            "voter_records": len(batch.voter_records),
        },
    }


def run_dry_run(
    pdf_path: Path,
    *,
    state_id: str,
    hash_salt: str | None,
    roll_year: int | None = None,
    roll_kind: str = DEFAULT_ROLL_KIND,
    language: str = DEFAULT_LANGUAGE,
    source_label: str = "Local dry-run PDF",
    source_url: str | None = None,
    parser_fn: ParserFn = parse_pdf,
) -> dict[str, Any]:
    if not hash_salt:
        raise ValueError(f"{EPIC_HASH_SALT_ENV} is required for dry-run ingestion")
    parsed_roll = parsed_roll_from_pdf(
        pdf_path,
        state_id=state_id,
        roll_year=roll_year,
        roll_kind=roll_kind,
        language=language,
        source_label=source_label,
        source_url=source_url,
        parser_fn=parser_fn,
    )
    batch = build_ingestion_batch(parsed_roll, hash_salt=hash_salt)
    return safe_report(batch)


def failure_report(message: str) -> dict[str, Any]:
    return {
        "dry_run": True,
        "safe_to_load": False,
        "error": message,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a local SIR roll PDF ingestion path.")
    parser.add_argument("--pdf", required=True, type=Path, help="Local PDF path; raw PDFs stay outside Git.")
    parser.add_argument("--state", required=True, help="Canonical state id, for example IN-MH.")
    parser.add_argument("--dry-run", action="store_true", help="Required; no DB writes or exports are performed.")
    parser.add_argument("--roll-year", type=int, help="Override parser revision_year metadata.")
    parser.add_argument("--roll-kind", default=DEFAULT_ROLL_KIND)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--source-label", default="Local dry-run PDF")
    parser.add_argument("--source-url")
    return parser


def main(argv: list[str] | None = None, *, parser_fn: ParserFn = parse_pdf) -> int:
    args = build_parser().parse_args(argv)
    if not args.dry_run:
        print(json.dumps(failure_report("--dry-run is required; this command does not perform live loads"), indent=2))
        return 2

    try:
        report = run_dry_run(
            args.pdf,
            state_id=args.state,
            hash_salt=os.environ.get(EPIC_HASH_SALT_ENV),
            roll_year=args.roll_year,
            roll_kind=args.roll_kind,
            language=args.language,
            source_label=args.source_label,
            source_url=args.source_url,
            parser_fn=parser_fn,
        )
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
