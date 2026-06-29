"""Small API DTO helpers that avoid exposing sensitive voter fields."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PublicVoterRecord:
    state_id: str
    ac_number: int | None
    part_number: int | None
    serial_number: int | None
    display_name: str
    roll_year: int
    roll_kind: str
    data_quality: str
    source_label: str
    confidence: float
    epic_hint: str | None = None

    def to_dict(self) -> dict[str, object | None]:
        return asdict(self)


@dataclass(frozen=True)
class InternalVoterRecord:
    state_id: str
    ac_number: int | None
    part_number: int | None
    serial_number: int | None
    name: str
    roll_year: int
    roll_kind: str
    data_quality: str
    source_label: str
    confidence: float
    epic_last4: str | None = None


def redact_voter_record(record: InternalVoterRecord) -> PublicVoterRecord:
    return PublicVoterRecord(
        state_id=record.state_id,
        ac_number=record.ac_number,
        part_number=record.part_number,
        serial_number=record.serial_number,
        display_name=record.name,
        roll_year=record.roll_year,
        roll_kind=record.roll_kind,
        data_quality=record.data_quality,
        source_label=record.source_label,
        confidence=record.confidence,
        epic_hint=("***" + record.epic_last4) if record.epic_last4 else None,
    )
