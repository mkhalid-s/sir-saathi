"""Deterministic guidance rules for SIR voter situations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .state_registry import StateConfig, load_all_states
from .translations import translate_message

Status = Literal["yes", "no", "unknown"]
Situation = Literal[
    "existing_voter",
    "new_voter",
    "missing_name",
    "shifted_address",
    "correction",
    "deceased_family",
    "duplicate_entry",
    "portal_failed",
]
Priority = Literal["low", "medium", "high", "urgent"]


@dataclass(frozen=True)
class GuidanceInput:
    state_id: str
    situation: Situation
    blo_visited: Status = "unknown"
    enumeration_form_received: Status = "unknown"
    enumeration_form_submitted: Status = "unknown"
    current_roll_found: Status = "unknown"
    base_roll_found: Status = "unknown"
    today: date | None = None


@dataclass(frozen=True)
class GuidanceResult:
    priority: Priority
    title: str
    summary: str
    actions: tuple[str, ...]
    documents: tuple[str, ...]
    official_links: tuple[str, ...]
    deadline: date | None
    source_labels: tuple[str, ...]
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _first_on_or_after(today: date | None, *candidates: date | None) -> date | None:
    available = tuple(candidate for candidate in candidates if candidate is not None)
    if not available:
        return None
    if today is None:
        return available[0]
    return next((candidate for candidate in available if candidate >= today), available[-1])


def _deadline_for(state: StateConfig, case: Situation, today: date | None) -> date | None:
    if case in {"missing_name", "correction", "shifted_address", "new_voter"}:
        return _first_on_or_after(today, state.schedule.claims_end, state.schedule.final_roll_date)
    if case in {"existing_voter", "portal_failed"}:
        return _first_on_or_after(
            today,
            state.schedule.enumeration_end,
            state.schedule.claims_end,
            state.schedule.final_roll_date,
        )
    return _first_on_or_after(today, state.schedule.claims_end, state.schedule.final_roll_date)


def _base_links(state: StateConfig) -> tuple[str, ...]:
    links = [state.ceo_portal]
    links.extend(source.url for source in state.official_sources[:2])
    return tuple(dict.fromkeys(links))


def _source_labels(state: StateConfig) -> tuple[str, ...]:
    return tuple(source.label for source in state.official_sources)


def _schedule_warning(state: StateConfig, today: date | None, deadline: date | None, locale: str) -> tuple[str, ...]:
    if today is None or deadline is None:
        return ()
    if today > deadline:
        return (translate_message(locale, "guidance.warning.passed"),)
    remaining = (deadline - today).days
    if remaining <= 3:
        return (translate_message(locale, "guidance.warning.close"),)
    return ()


def get_guidance(
    request: GuidanceInput,
    states: dict[str, StateConfig] | None = None,
    *,
    locale: str = "en",
) -> GuidanceResult:
    registry = states or load_all_states()
    if request.state_id not in registry:
        raise ValueError(f"unknown state_id: {request.state_id}")
    state = registry[request.state_id]
    deadline = _deadline_for(state, request.situation, request.today)
    links = _base_links(state)
    labels = _source_labels(state)
    text = lambda key, values=None: translate_message(locale, key, values)
    form = lambda form_id: text(f"forms.{form_id}.label")
    warnings = list(_schedule_warning(state, request.today, deadline, locale))
    schedule_unavailable = state.schedule.status in {"schedule_unverified", "schedule_pending"}

    if request.situation == "existing_voter":
        revision_complete = state.schedule.status_on(request.today) == "final_roll_published" if request.today else (
            state.schedule.status == "final_roll_published"
        )
        enumeration_closed = bool(
            request.today
            and state.schedule.enumeration_end
            and request.today > state.schedule.enumeration_end
        )
        if schedule_unavailable:
            actions = [
                text("guidance.existing.check_current"),
                text("guidance.existing.check_notices"),
                text("guidance.existing.contact_unverified"),
            ]
        elif revision_complete:
            actions = [
                text("guidance.existing.check_final"),
                text("guidance.existing.current_remedy"),
                text("guidance.existing.keep_every"),
            ]
        elif enumeration_closed:
            actions = [
                text("guidance.existing.check_draft"),
                text("guidance.existing.file_claim"),
                text("guidance.existing.keep_every"),
            ]
        else:
            actions = [
                text("guidance.existing.verify"),
                text("guidance.existing.submit_enumeration"),
                text("guidance.existing.keep"),
            ]
        if not schedule_unavailable and (
            request.enumeration_form_received == "no" or request.blo_visited == "no"
        ):
            actions.insert(0, text("guidance.existing.contact_missing_form"))
            priority: Priority = "high"
        else:
            priority = "medium"
        return GuidanceResult(
            priority=priority,
            title=text("guidance.existing.title"),
            summary=(
                text("guidance.existing.summary_unverified")
                if schedule_unavailable
                else text("guidance.existing.summary_complete")
                if revision_complete
                else text("guidance.existing.summary")
            ),
            actions=tuple(actions),
            documents=(text("document.existing_reference"), text("document.changed_detail")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "new_voter":
        return GuidanceResult(
            priority="high",
            title=text("guidance.new.title"),
            summary=text("guidance.new.summary", {"form": form("form_6")}),
            actions=(
                text("guidance.new.eligibility"),
                text("guidance.new.prepare"),
                text("guidance.new.submit", {"form": form("form_6")}),
                text("guidance.new.track"),
            ),
            documents=(text("document.identity"), text("document.address"), text("document.age")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "missing_name":
        actions = [
            text("guidance.missing.search_again"),
            text("guidance.missing.check_roll"),
            text("guidance.missing.file_claim"),
            text("guidance.missing.contact"),
        ]
        if not schedule_unavailable and request.base_roll_found == "yes":
            actions.insert(2, text("guidance.missing.base_reference"))
        return GuidanceResult(
            priority="urgent",
            title=text("guidance.missing.title"),
            summary=text("guidance.missing.summary"),
            actions=tuple(actions),
            documents=(text("document.identity"), text("document.address"), text("document.previous_reference")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "shifted_address":
        return GuidanceResult(
            priority="high",
            title=text("guidance.shift.title"),
            summary=text("guidance.shift.summary"),
            actions=(
                text("guidance.shift.confirm_ac"),
                text("guidance.shift.prepare"),
                text("guidance.shift.submit", {"form": form("form_8")}),
                text("guidance.shift.verify_station"),
            ),
            documents=(text("document.address"), text("document.existing_reference")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "correction":
        return GuidanceResult(
            priority="medium",
            title=text("guidance.correction.title"),
            summary=text("guidance.correction.summary", {"form": form("form_8")}),
            actions=(
                text("guidance.correction.identify"),
                text("guidance.correction.prepare"),
                text("guidance.correction.submit", {"form": form("form_8")}),
            ),
            documents=(text("document.existing_reference"), text("document.correction")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "deceased_family":
        return GuidanceResult(
            priority="medium",
            title=text("guidance.deceased.title"),
            summary=text("guidance.deceased.summary"),
            actions=(
                text("guidance.deceased.confirm"),
                text("guidance.deceased.prepare"),
                text("guidance.deceased.submit", {"form": form("form_7")}),
                text("guidance.deceased.keep"),
            ),
            documents=(text("document.deletion"), text("document.contact")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "duplicate_entry":
        return GuidanceResult(
            priority="medium",
            title=text("guidance.duplicate.title"),
            summary=text("guidance.duplicate.summary"),
            actions=(
                text("guidance.duplicate.note"),
                text("guidance.duplicate.contact"),
                text("guidance.duplicate.submit"),
            ),
            documents=(text("document.existing_reference"), text("document.address")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "portal_failed":
        return GuidanceResult(
            priority="high",
            title=text("guidance.portal.title"),
            summary=text("guidance.portal.summary"),
            actions=(
                text("guidance.portal.retry"),
                text("guidance.portal.record"),
                text("guidance.portal.submit"),
            ),
            documents=(text("document.form_details"), text("document.identity"), text("document.address")),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    raise ValueError(f"unsupported situation: {request.situation}")
