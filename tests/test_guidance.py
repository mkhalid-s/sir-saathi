from datetime import date

from pipeline.sir_saathi_pipeline.guidance import GuidanceInput, get_guidance


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
        )
    )
    assert result.priority == "high"
    assert "Contact your BLO" in result.actions[0]


def test_west_bengal_guidance_uses_official_sources() -> None:
    result = get_guidance(GuidanceInput(state_id="IN-WB", situation="correction"))
    assert result.priority == "medium"
    assert result.deadline == date(2026, 2, 28)
    assert any("CEO West Bengal" in label for label in result.source_labels)


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
