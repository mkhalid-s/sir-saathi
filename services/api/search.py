"""Scoped search contract and in-memory pilot search implementation."""

from __future__ import annotations

from dataclasses import dataclass

from .models import InternalVoterRecord, PublicVoterRecord, redact_voter_record


@dataclass(frozen=True)
class SearchRequest:
    state_id: str
    query: str
    ac_number: int
    part_number: int | None = None
    limit: int = 10


def validate_search_scope(request: SearchRequest) -> None:
    if not isinstance(request.query, str):
        raise ValueError("query must be a string")
    if len(request.query.strip()) < 2:
        raise ValueError("query must contain at least two characters")
    if request.ac_number is None:
        raise ValueError("name search must be scoped by Assembly Constituency")
    if request.part_number is not None and request.ac_number is None:
        raise ValueError("part_number search also requires ac_number")
    if request.limit < 1 or request.limit > 20:
        raise ValueError("limit must be between 1 and 20")


def search_records(request: SearchRequest, records: list[InternalVoterRecord]) -> list[PublicVoterRecord]:
    validate_search_scope(request)
    query = request.query.casefold().strip()
    matches: list[InternalVoterRecord] = []
    for record in records:
        if record.state_id != request.state_id:
            continue
        if record.ac_number != request.ac_number:
            continue
        if request.part_number is not None and record.part_number != request.part_number:
            continue
        if query in record.name.casefold():
            matches.append(record)
    matches = sorted(matches, key=lambda item: (-item.confidence, item.serial_number or 0))
    return [redact_voter_record(record) for record in matches[: request.limit]]


def redact_backend_results(request: SearchRequest, records: list[InternalVoterRecord]) -> list[PublicVoterRecord]:
    """Redact already-ranked backend rows and reject any scope/limit contract breach."""

    validate_search_scope(request)
    if len(records) > request.limit:
        raise ValueError("search backend returned more than the requested limit")
    for record in records:
        if record.state_id != request.state_id or record.ac_number != request.ac_number:
            raise ValueError("search backend returned a record outside the requested state/AC scope")
        if request.part_number is not None and record.part_number != request.part_number:
            raise ValueError("search backend returned a record outside the requested part scope")
    return [redact_voter_record(record) for record in records]
