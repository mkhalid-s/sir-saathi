from datetime import date

from pipeline.sir_saathi_pipeline.guidance import GuidanceInput, get_guidance
from pipeline.sir_saathi_pipeline.state_registry import load_all_states


def test_all_jurisdictions_and_situations_obey_phase_safety_matrix() -> None:
    states = load_all_states()
    situations = (
        "existing_voter",
        "missing_name",
        "new_voter",
        "shifted_address",
        "correction",
        "deceased_family",
        "duplicate_entry",
        "portal_failed",
    )
    today = date(2026, 8, 1)
    assert len(states) == 36
    for state_id, state in states.items():
        phase = state.schedule.status_on(today)
        for situation in situations:
            result = get_guidance(GuidanceInput(state_id=state_id, situation=situation, today=today))
            assert result.title and result.summary and result.actions and result.documents
            if state.schedule.status in {"schedule_unverified", "schedule_pending"}:
                assert result.deadline is None
            else:
                assert result.deadline is not None

        normal = get_guidance(GuidanceInput(state_id=state_id, situation="existing_voter", today=today))
        stale = get_guidance(GuidanceInput(
            state_id=state_id,
            situation="existing_voter",
            blo_visited="no",
            enumeration_form_received="yes",
            enumeration_form_submitted="no",
            today=today,
        ))
        if phase in {"pre_enumeration", "enumeration_open"}:
            assert stale.priority == "high"
        else:
            assert stale == normal

        missing = get_guidance(GuidanceInput(
            state_id=state_id,
            situation="existing_voter",
            current_roll_found="no",
            today=today,
        ))
        assert missing.priority == "urgent"
        assert "Treat this as urgent" in missing.actions[0]
        if phase == "final_roll_published":
            assert "reviewed revision schedule is complete" in normal.summary
            assert "final/current electoral roll" in normal.actions[0]


def test_missing_name_is_urgent_and_uses_claims_deadline() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="missing_name",
            current_roll_found="no",
            base_roll_found="yes",
            today=date(2026, 8, 20),
        )
    )
    assert result.priority == "urgent"
    assert result.deadline == date(2026, 9, 4)
    assert any("older/base-roll" in action for action in result.actions)


def test_existing_voter_without_blo_visit_is_high_priority() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="existing_voter",
            blo_visited="no",
            enumeration_form_received="no",
            today=date(2026, 7, 1),
        )
    )
    assert result.priority == "high"
    assert "Contact your BLO" in result.actions[0]


def test_existing_voter_received_form_and_missing_roll_match_pwa_priority_rules() -> None:
    received = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="existing_voter",
            enumeration_form_received="yes",
            enumeration_form_submitted="no",
            today=date(2026, 7, 1),
        )
    )
    assert received.priority == "high"
    assert "Submit the received enumeration form" in received.actions[0]

    missing = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="existing_voter",
            current_roll_found="no",
            today=date(2026, 8, 1),
        )
    )
    assert missing.priority == "urgent"
    assert missing.title == "Resolve your missing current-roll entry"
    assert "Treat this as urgent" in missing.actions[0]


def test_completed_revision_ignores_stale_enumeration_answers() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="existing_voter",
            blo_visited="no",
            enumeration_form_received="yes",
            enumeration_form_submitted="no",
            today=date(2026, 10, 8),
        )
    )
    assert result.priority == "medium"
    assert "final/current electoral roll" in result.actions[0]
    assert all("enumeration form" not in action.casefold() for action in result.actions)


def test_existing_voter_advances_to_claims_deadline_after_enumeration() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="existing_voter",
            today=date(2026, 8, 1),
        )
    )
    assert result.deadline == date(2026, 9, 4)
    assert not result.warnings
    assert "draft/current electoral roll" in result.actions[0]
    assert all("submit it before the enumeration deadline" not in action for action in result.actions)


def test_west_bengal_guidance_uses_official_sources() -> None:
    result = get_guidance(GuidanceInput(state_id="IN-WB", situation="correction"))
    assert result.priority == "medium"
    assert result.deadline == date(2026, 2, 28)
    assert any("CEO West Bengal" in label for label in result.source_labels)


def test_unverified_schedule_guidance_does_not_invent_sir_steps_or_deadlines() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-HP",
            situation="existing_voter",
            today=date(2026, 8, 1),
        )
    )
    assert result.deadline is None
    assert "official jurisdiction notice" in result.summary
    assert any("official CEO notices" in action for action in result.actions)
    assert all("enumeration deadline" not in action for action in result.actions)


def test_officially_pending_schedule_guidance_does_not_invent_dates() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-HP",
            situation="existing_voter",
            blo_visited="no",
            enumeration_form_received="no",
            today=date(2026, 8, 1),
        )
    )
    assert result.deadline is None
    assert result.priority == "medium"
    assert "ECI SIR Phase III deferral notice" in result.source_labels
    assert all("Contact your BLO" not in action for action in result.actions)
    assert all("enumeration deadline" not in action for action in result.actions)
    missing = get_guidance(
        GuidanceInput(state_id="IN-HP", situation="missing_name", base_roll_found="yes")
    )
    assert all("older/base-roll" not in action for action in missing.actions)


def test_shared_phase_three_schedule_drives_source_backed_guidance() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-AP",
            situation="existing_voter",
            today=date(2026, 8, 1),
        )
    )
    assert result.deadline == date(2026, 8, 20)
    assert "ECI SIR Phase III schedule" in result.source_labels
    assert not result.warnings


def test_completed_revision_never_sends_voter_back_to_enumeration() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-GA",
            situation="existing_voter",
            today=date(2026, 8, 1),
        )
    )
    assert "final/current electoral roll" in result.actions[0]
    assert "reviewed revision schedule is complete" in result.summary
    assert all("enumeration" not in action.casefold() for action in result.actions)


def test_deadline_warning_when_close() -> None:
    result = get_guidance(
        GuidanceInput(
            state_id="IN-MH",
            situation="portal_failed",
            today=date(2026, 7, 28),
        )
    )
    assert result.warnings
    assert "deadline is very close" in result.warnings[0]
