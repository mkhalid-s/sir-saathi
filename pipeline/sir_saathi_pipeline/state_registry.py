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
DEFAULT_JURISDICTION_PATH = ROOT / "config" / "jurisdictions.json"
DEFAULT_SCHEDULE_PATH = ROOT / "config" / "sir-schedules.json"
VALID_CAPABILITIES = {
    "guidance_only",
    "official_link_search",
    "pilot_indexed_search",
    "validated_indexed_search",
}
VALID_PROVENANCE_CONFIDENCE = {"official", "reported", "unverified"}


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

    def status_on(self, today: date) -> str:
        """Derive the user-facing phase from reviewed schedule dates."""
        if self.enumeration_start and today < self.enumeration_start:
            return "pre_enumeration"
        if self.enumeration_start and self.enumeration_end and today <= self.enumeration_end:
            return "enumeration_open"
        if self.draft_roll_date and today < self.draft_roll_date:
            return "pre_draft_publication"
        if self.draft_roll_date and self.claims_end and today <= self.claims_end:
            return "claims_and_objections_open"
        if self.final_roll_date and today < self.final_roll_date:
            return "claims_disposal"
        if self.final_roll_date and today >= self.final_roll_date:
            return "final_roll_published"
        return self.status


@dataclass(frozen=True)
class DataSource:
    label: str
    url: str
    source_type: str
    last_verified: date
    notes: str = ""


@dataclass(frozen=True)
class ScheduleProvenance:
    label: str
    source_type: str
    confidence: str
    notes: str


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
    schedule_provenance: ScheduleProvenance
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
    provenance_raw = _require(data, "schedule_provenance")
    provenance_confidence = _require(provenance_raw, "confidence")
    if provenance_confidence not in VALID_PROVENANCE_CONFIDENCE:
        raise ValueError(f"invalid schedule provenance confidence: {provenance_confidence}")
    provenance_label = _require(provenance_raw, "label")
    provenance_source_type = _require(provenance_raw, "source_type")
    matching_source = next((source for source in sources if source.label == provenance_label), None)
    if matching_source is None:
        raise ValueError(f"schedule provenance source is not listed: {provenance_label}")
    if provenance_source_type != matching_source.source_type:
        raise ValueError("schedule provenance source_type must match the listed source")
    if provenance_confidence == "official" and provenance_source_type != "official_portal":
        raise ValueError("official schedule provenance must come from an official portal")
    provenance = ScheduleProvenance(
        label=provenance_label,
        source_type=provenance_source_type,
        confidence=provenance_confidence,
        notes=_require(provenance_raw, "notes"),
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
        schedule_provenance=provenance,
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


def load_jurisdiction_catalogue(path: str | Path = DEFAULT_JURISDICTION_PATH) -> dict[str, StateConfig]:
    catalogue_path = Path(path)
    with catalogue_path.open(encoding="utf-8") as handle:
        catalogue = json.load(handle)
    source = _require(catalogue, "source")
    source_label = _require(source, "label")
    source_url = _require(source, "url")
    source_verified = _require(source, "last_verified")
    states: dict[str, StateConfig] = {}
    eci_codes: set[str] = set()
    for jurisdiction in _require(catalogue, "jurisdictions"):
        state_id = _require(jurisdiction, "state_id")
        eci_state_code = _require(jurisdiction, "eci_state_code")
        if state_id in states:
            raise ValueError(f"duplicate jurisdiction state_id: {state_id}")
        if eci_state_code in eci_codes:
            raise ValueError(f"duplicate jurisdiction eci_state_code: {eci_state_code}")
        ceo_portal = _require(jurisdiction, "ceo_portal")
        state = parse_state_config(
            {
                **jurisdiction,
                "sir_schedule": {
                    "phase": "Not verified",
                    "qualifying_date": None,
                    "enumeration_start": None,
                    "enumeration_end": None,
                    "draft_roll_date": None,
                    "claims_start": None,
                    "claims_end": None,
                    "final_roll_date": None,
                    "status": "schedule_unverified",
                },
                "schedule_provenance": {
                    "label": source_label,
                    "source_type": "official_portal",
                    "confidence": "unverified",
                    "notes": "The official CEO link is verified from ECI's directory, but this jurisdiction's current SIR schedule has not yet been verified.",
                },
                "official_sources": [
                    {
                        "label": f"CEO {jurisdiction['name']}",
                        "url": ceo_portal,
                        "source_type": "official_portal",
                        "last_verified": source_verified,
                        "notes": "Official jurisdiction election portal listed by ECI.",
                    },
                    {
                        "label": "ECI voters portal",
                        "url": "https://voters.eci.gov.in/",
                        "source_type": "official_portal",
                        "last_verified": source_verified,
                        "notes": "Official national portal for voter services and electoral search.",
                    },
                    {
                        "label": source_label,
                        "url": source_url,
                        "source_type": "official_portal",
                        "last_verified": source_verified,
                        "notes": "ECI directory used to verify the jurisdiction CEO portal link.",
                    },
                ],
                "base_roll_years": [],
                "historical_source_shape": "Not yet assessed.",
                "current_roll_source_shape": "Official CEO and ECI voter-service links only; source files are not indexed.",
                "data_capability": "official_link_search",
                "parser_status": "Not assessed; no electoral-roll data is indexed.",
                "public_launch_ready": False,
                "privacy_notes": "Guidance and official links only until schedule, parser, legal, privacy, and quality gates pass.",
            }
        )
        states[state_id] = state
        eci_codes.add(eci_state_code)
    return states


def load_all_states(state_dir: str | Path = DEFAULT_STATE_DIR) -> dict[str, StateConfig]:
    directory = Path(state_dir)
    configured = [load_state(path) for path in sorted(directory.glob("*.json"))]
    configured_ids = [state.state_id for state in configured]
    if len(configured_ids) != len(set(configured_ids)):
        raise ValueError("duplicate state_id in state configuration overrides")
    if directory.resolve() == DEFAULT_STATE_DIR.resolve():
        states = apply_schedule_overrides(load_jurisdiction_catalogue())
    else:
        states = {}
    states.update({state.state_id: state for state in configured})
    return dict(sorted(states.items()))


def apply_schedule_overrides(
    states: dict[str, StateConfig],
    path: str | Path = DEFAULT_SCHEDULE_PATH,
) -> dict[str, StateConfig]:
    """Apply reviewed, shared official schedules without duplicating state metadata."""

    from dataclasses import replace

    schedule_path = Path(path)
    with schedule_path.open(encoding="utf-8") as handle:
        catalogue = json.load(handle)
    source_raw = _require(catalogue, "source")
    if _require(source_raw, "source_type") != "official_portal":
        raise ValueError("reviewed nationwide schedule source must be an official portal")

    updated = dict(states)
    seen: set[str] = set()
    for group in _require(catalogue, "schedule_groups"):
        group_source_raw = group.get("source", source_raw)
        source = DataSource(
            label=_require(group_source_raw, "label"),
            url=_require(group_source_raw, "url"),
            source_type=_require(group_source_raw, "source_type"),
            last_verified=_require_date(group_source_raw, "last_verified"),
            notes=_require(group_source_raw, "notes"),
        )
        if source.source_type != "official_portal":
            raise ValueError("reviewed schedule group source must be an official portal")
        schedule = SirSchedule(
            phase=_require(group, "phase"),
            qualifying_date=_parse_date(group.get("qualifying_date")),
            enumeration_start=_parse_date(group.get("enumeration_start")),
            enumeration_end=_parse_date(group.get("enumeration_end")),
            draft_roll_date=_parse_date(group.get("draft_roll_date")),
            claims_start=_parse_date(group.get("claims_start")),
            claims_end=_parse_date(group.get("claims_end")),
            final_roll_date=_parse_date(group.get("final_roll_date")),
            status=_require(group, "status"),
        )
        if not schedule.final_roll_date:
            raise ValueError("reviewed schedule groups require a final-roll date")
        for state_id in _require(group, "state_ids"):
            if state_id in seen:
                raise ValueError(f"duplicate reviewed schedule state_id: {state_id}")
            if state_id not in updated:
                raise ValueError(f"unknown reviewed schedule state_id: {state_id}")
            seen.add(state_id)
            state = updated[state_id]
            provenance = ScheduleProvenance(
                label=source.label,
                source_type=source.source_type,
                confidence="official",
                notes=source.notes,
            )
            updated[state_id] = replace(
                state,
                schedule=schedule,
                schedule_provenance=provenance,
                official_sources=(source, *state.official_sources),
            )
    return updated
