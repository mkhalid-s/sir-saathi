"""Fail-closed registry for roll parser families."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .maharashtra_2002 import parse_pdf as parse_maharashtra_2002
from .maharashtra_current import parse_pdf as parse_maharashtra_current

ParserFn = Callable[[Path], tuple[dict[str, Any], list[dict[str, Any]], list[str]]]


@dataclass(frozen=True)
class ParserSpec:
    parser_hint: str
    parser_name: str
    state_ids: tuple[str, ...]
    roll_kinds: tuple[str, ...]
    validation_status: str
    ingestion_ready: bool
    parser: ParserFn


PARSERS = {
    "parse_2002": ParserSpec(
        parser_hint="parse_2002",
        parser_name="maharashtra_2002_virgod3",
        state_ids=("IN-MH",),
        roll_kinds=("historical_base_roll", "base_roll"),
        validation_status="pilot_validated",
        ingestion_ready=True,
        parser=parse_maharashtra_2002,
    ),
    "maharashtra_current_unicode_v1": ParserSpec(
        parser_hint="maharashtra_current_unicode_v1",
        parser_name="maharashtra_current_unicode_v1",
        state_ids=("IN-MH",),
        roll_kinds=("current_roll", "draft_roll", "final_roll", "supplement"),
        validation_status="synthetic_fixture_only",
        ingestion_ready=False,
        parser=parse_maharashtra_current,
    ),
}


def parser_spec(parser_hint: str) -> ParserSpec:
    if parser_hint not in PARSERS:
        raise ValueError(f"unsupported parser_hint: {parser_hint}")
    return PARSERS[parser_hint]


def validate_parser_scope(parser_hint: str, *, state_id: str, roll_kind: str, require_ready: bool = True) -> ParserSpec:
    spec = parser_spec(parser_hint)
    if state_id not in spec.state_ids:
        raise ValueError(f"parser_hint {parser_hint} is not valid for state {state_id}")
    if roll_kind not in spec.roll_kinds:
        raise ValueError(f"parser_hint {parser_hint} is not valid for roll_kind {roll_kind}")
    if require_ready and not spec.ingestion_ready:
        raise ValueError(
            f"parser_hint {parser_hint} is not ingestion-ready; status={spec.validation_status}"
        )
    return spec
