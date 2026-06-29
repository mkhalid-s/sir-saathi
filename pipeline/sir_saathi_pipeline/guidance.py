"""Deterministic guidance rules for SIR voter situations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from .state_registry import StateConfig, load_all_states

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


def _deadline_for(state: StateConfig, case: Situation) -> date | None:
    if case in {"missing_name", "correction", "shifted_address", "new_voter"}:
        return state.schedule.claims_end or state.schedule.final_roll_date
    if case in {"existing_voter", "portal_failed"}:
        return state.schedule.enumeration_end or state.schedule.claims_end or state.schedule.final_roll_date
    return state.schedule.claims_end or state.schedule.final_roll_date


def _base_links(state: StateConfig) -> tuple[str, ...]:
    links = [state.ceo_portal]
    links.extend(source.url for source in state.official_sources[:2])
    return tuple(dict.fromkeys(links))


def _source_labels(state: StateConfig) -> tuple[str, ...]:
    return tuple(source.label for source in state.official_sources)


def _schedule_warning(state: StateConfig, today: date | None, deadline: date | None) -> tuple[str, ...]:
    if today is None or deadline is None:
        return ()
    if today > deadline:
        return ("The listed deadline appears to have passed. Check the official CEO/ECI portal for late remedies or appeal options.",)
    remaining = (deadline - today).days
    if remaining <= 3:
        return ("The deadline is very close. Prefer the official portal and also contact the BLO/ERO offline.",)
    return ()


def get_guidance(request: GuidanceInput, states: dict[str, StateConfig] | None = None) -> GuidanceResult:
    registry = states or load_all_states()
    if request.state_id not in registry:
        raise ValueError(f"unknown state_id: {request.state_id}")
    state = registry[request.state_id]
    deadline = _deadline_for(state, request.situation)
    links = _base_links(state)
    labels = _source_labels(state)
    warnings = list(_schedule_warning(state, request.today, deadline))

    if request.situation == "existing_voter":
        actions = [
            "Confirm your name in the current electoral roll using the official portal or local BLO support.",
            "If you receive a SIR enumeration form, verify the pre-filled details and submit it before the enumeration deadline.",
            "Keep the acknowledgement copy or submission confirmation safely.",
        ]
        if request.enumeration_form_received == "no" or request.blo_visited == "no":
            actions.insert(0, "Contact your BLO or local ERO office because the enumeration form has not reached you yet.")
            priority: Priority = "high"
        else:
            priority = "medium"
        return GuidanceResult(
            priority=priority,
            title="Verify and submit your SIR details",
            summary="You appear to be an existing voter. The safest next step is to verify your roll entry and complete the SIR enumeration process.",
            actions=tuple(actions),
            documents=("Existing voter ID or EPIC reference", "Any document needed to correct changed details"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "new_voter":
        return GuidanceResult(
            priority="high",
            title="Register as a new voter",
            summary="If you are eligible but not registered, use Form 6 through the official voter services channel or submit it offline to election officials.",
            actions=(
                "Check eligibility for the state qualifying date.",
                "Prepare identity, address, and age proof.",
                "Submit Form 6 on the official portal or through the ERO/BLO route.",
                "Track the application and respond quickly if officials ask for clarification.",
            ),
            documents=("Identity proof", "Current address proof", "Age or date-of-birth proof"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "missing_name":
        actions = [
            "Search again with alternate spelling, age, district, AC, and family details.",
            "Check whether your name appears in the draft/current roll through official channels.",
            "If still missing, file the appropriate claim during the claims and objections window.",
            "Contact BLO/ERO offline and keep acknowledgement or complaint details.",
        ]
        if request.base_roll_found == "yes":
            actions.insert(2, "Mention that your older/base-roll record appears to exist when you contact officials.")
        return GuidanceResult(
            priority="urgent",
            title="Act quickly on a missing name",
            summary="A missing name during SIR needs fast official follow-up, especially during the claims and objections window.",
            actions=tuple(actions),
            documents=("Identity proof", "Address proof", "Any previous voter ID or roll reference", "Acknowledgement copies"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "shifted_address":
        return GuidanceResult(
            priority="high",
            title="Update your shifted address",
            summary="If your address changed, use the official correction/shift route so the roll and polling station match your current residence.",
            actions=(
                "Confirm whether the shift is within the same AC or to another AC/state.",
                "Prepare current address proof.",
                "Use Form 8 or the official shift/correction workflow as applicable.",
                "Verify the updated polling station after disposal.",
            ),
            documents=("Current address proof", "Existing voter ID or EPIC reference"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "correction":
        return GuidanceResult(
            priority="medium",
            title="Correct voter details",
            summary="Use Form 8 for spelling, age, address, replacement EPIC, or similar corrections through official channels.",
            actions=(
                "Identify the exact field that is wrong.",
                "Prepare a document supporting the correct value.",
                "Submit Form 8 online or through the local election office.",
                "Track the request and verify the corrected roll entry.",
            ),
            documents=("Existing voter ID or EPIC reference", "Document supporting the correction"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "deceased_family":
        return GuidanceResult(
            priority="medium",
            title="Report a deceased family member entry",
            summary="Use the official objection/deletion route only with supporting details and documents.",
            actions=(
                "Confirm the entry in the current roll.",
                "Prepare available supporting record for the deceased elector.",
                "Submit the official deletion/objection request through Form 7 or local ERO/BLO route.",
                "Keep acknowledgement details for follow-up.",
            ),
            documents=("Supporting record for deletion request", "Your contact details for official follow-up"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "duplicate_entry":
        return GuidanceResult(
            priority="medium",
            title="Report or resolve duplicate entries",
            summary="Duplicate entries should be corrected through official ERO/BLO channels so the valid entry is retained.",
            actions=(
                "Note both duplicate entries without sharing them publicly.",
                "Contact the BLO/ERO and ask which entry should remain active.",
                "Submit the official objection/correction form if instructed.",
            ),
            documents=("Existing voter ID or roll references", "Current address proof if the duplicate relates to a shift"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    if request.situation == "portal_failed":
        return GuidanceResult(
            priority="high",
            title="Use offline fallback if the portal fails",
            summary="Online portal issues should not block SIR action. Use the BLO/ERO offline route and keep proof of attempts.",
            actions=(
                "Retry the official portal once with a stable connection and correct mobile/EPIC details.",
                "Take note of the error and time of failure without exposing private details publicly.",
                "Contact the BLO or ERO office before the deadline.",
                "Submit the relevant form offline and keep acknowledgement.",
            ),
            documents=("Relevant form details", "Identity proof", "Address proof", "Acknowledgement or error reference if available"),
            official_links=links,
            deadline=deadline,
            source_labels=labels,
            warnings=tuple(warnings),
        )

    raise ValueError(f"unsupported situation: {request.situation}")
