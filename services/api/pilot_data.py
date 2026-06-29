"""Sanitized pilot search data for local API demos and tests."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .models import InternalVoterRecord

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "mh_pilot_records.json"


@lru_cache(maxsize=1)
def load_sanitized_pilot_records(path: str | Path = DEFAULT_FIXTURE) -> tuple[InternalVoterRecord, ...]:
    fixture_path = Path(path)
    with fixture_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    return tuple(InternalVoterRecord(**row) for row in rows)


def validate_pilot_records(records: tuple[InternalVoterRecord, ...]) -> dict[str, int]:
    total = len(records)
    redaction_ready = sum(1 for record in records if not record.epic_last4 or len(record.epic_last4) == 4)
    scoped = sum(1 for record in records if record.ac_number is not None and record.part_number is not None)
    return {"total": total, "redaction_ready": redaction_ready, "scoped": scoped}
