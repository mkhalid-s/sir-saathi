"""Typed loader for public state SIR configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Literal

Capability = Literal[
    "guidance_only",
    "official_link_search",
    "pilot_indexed_search",
    "validated_indexed_search",
]

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_DIR = ROOT / "config" / "states"
VALID_CAPABILITIES = {
    "guidance_only",
    "official_link_search",
    "pilot_indexed_search",
    "validated_indexed_search",
}


@dataclass(frozen=True)
class SirSchedule:
    phase: str
    qualifying_date: date | None
    enumeration_start: date | None
    enumeration_end: date | None
    draft_roll_date: date | None
    claims_start: date | None
    claims_end: date | None
    final_roll_date: date | None
    status: str


@dataclass(frozen=True)
class DataSource:
    label: str
    url: str
    source_type: str
    last_verified: date
    notes: str = ""


@dataclass(frozen=True)
class StateConfig:
    state_id: str
    eci_state_code: str
    name: str
    short_name: str
    languages: tuple[str, ...]
    scripts: tuple[str, ...]
    default_language: str
    schedule: SirSchedule
    ceo_portal: str
    official_sources: tuple[DataSource, ...]
    base_roll_years: tuple[int, ...]
    historical_source_shape: str
    current_roll_source_shape: str
    data_capability: Capability
    parser_status: str
    public_launch_ready: bool
    privacy_notes: str

    @property
    def is_search_enabled(self) -> bool:
        return self.data_capability in {"pilot_indexed_search", "validated_indexed_search"}


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _require_date(data: dict[str, Any], key: str) -> date:
    value = _parse_date(_require(data, key))
    if value is None:
        raise ValueError(f"missing required date: {key}")
    return value


def _require(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"missing required key: {key}")
    return data[key]


def parse_state_config(data: dict[str, Any]) -> StateConfig:
    capability = _require(data, "data_capability")
    if capability not in VALID_CAPABILITIES:
        raise ValueError(f"invalid data_capability: {capability}")

    schedule_raw = _require(data, "sir_schedule")
    schedule = SirSchedule(
        phase=_require(schedule_raw, "phase"),
        qualifying_date=_parse_date(schedule_raw.get("qualifying_date")),
        enumeration_start=_parse_date(schedule_raw.get("enumeration_start")),
        enumeration_end=_parse_date(schedule_raw.get("enumeration_end")),
        draft_roll_date=_parse_date(schedule_raw.get("draft_roll_date")),
        claims_start=_parse_date(schedule_raw.get("claims_start")),
        claims_end=_parse_date(schedule_raw.get("claims_end")),
        final_roll_date=_parse_date(schedule_raw.get("final_roll_date")),
        status=_require(schedule_raw, "status"),
    )

    sources = tuple(
        DataSource(
            label=_require(source, "label"),
            url=_require(source, "url"),
            source_type=_require(source, "source_type"),
            last_verified=_require_date(source, "last_verified"),
            notes=source.get("notes", ""),
        )
        for source in _require(data, "official_sources")
    )

    return StateConfig(
        state_id=_require(data, "state_id"),
        eci_state_code=_require(data, "eci_state_code"),
        name=_require(data, "name"),
        short_name=_require(data, "short_name"),
        languages=tuple(_require(data, "languages")),
        scripts=tuple(_require(data, "scripts")),
        default_language=_require(data, "default_language"),
        schedule=schedule,
        ceo_portal=_require(data, "ceo_portal"),
        official_sources=sources,
        base_roll_years=tuple(int(year) for year in _require(data, "base_roll_years")),
        historical_source_shape=_require(data, "historical_source_shape"),
        current_roll_source_shape=_require(data, "current_roll_source_shape"),
        data_capability=capability,  # type: ignore[assignment]
        parser_status=_require(data, "parser_status"),
        public_launch_ready=bool(_require(data, "public_launch_ready")),
        privacy_notes=_require(data, "privacy_notes"),
    )


def load_state(path: str | Path) -> StateConfig:
    state_path = Path(path)
    with state_path.open(encoding="utf-8") as handle:
        return parse_state_config(json.load(handle))


def load_all_states(state_dir: str | Path = DEFAULT_STATE_DIR) -> dict[str, StateConfig]:
    directory = Path(state_dir)
    states = [load_state(path) for path in sorted(directory.glob("*.json"))]
    return {state.state_id: state for state in states}
