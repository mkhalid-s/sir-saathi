from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.parsers.maharashtra_current import parse_text, parse_voter_line
from pipeline.sir_saathi_pipeline.parsers.registry import parser_spec, validate_parser_scope

FIRST_SYNTHETIC_EPIC = "ABC" + "1234567"
SECOND_SYNTHETIC_EPIC = "XYZ" + "7654321"
SYNTHETIC_CURRENT_ROLL = f"""Revision Year: 2026
District: Mumbai Suburban
Assembly Constituency: 172 - Anushakti Nagar
Part No: 21
Total Electors: 2
1 | {FIRST_SYNTHETIC_EPIC} | Name: Asha Patil | Father: Mohan Patil | House: H-1 | Age: 34 | Gender: Female
2 | {SECOND_SYNTHETIC_EPIC} | Name: Rahul Deshmukh | Mother: Seema Deshmukh | House: H-2 | Age: 29 | Gender: Male
"""


def test_current_roll_text_parser_emits_normalized_ingestion_contract() -> None:
    metadata, voters, failures = parse_text(SYNTHETIC_CURRENT_ROLL)
    assert failures == []
    assert metadata["source_encoding"] == "unicode"
    assert metadata["revision_year"] == 2026
    assert metadata["ac_number"] == 172
    assert metadata["part_number"] == 21
    assert metadata["district_name"] == "Mumbai Suburban"
    assert len(voters) == 2
    assert voters[0]["voter_name"] == "Asha Patil"
    assert voters[0]["relation_type"] == "father"
    assert voters[0]["gender"] == "F"


def test_current_roll_parser_accounts_for_unparsed_candidate_lines() -> None:
    metadata, voters, failures = parse_text(
        SYNTHETIC_CURRENT_ROLL.replace(
            f"2 | {SECOND_SYNTHETIC_EPIC} | Name: Rahul Deshmukh | Mother: Seema Deshmukh | House: H-2 | Age: 29 | Gender: Male",
            "2 | malformed record",
        )
    )
    assert metadata["total_voters"] == 2
    assert len(voters) == 1
    assert len(failures) == 2
    assert "unparsed voter record" in failures[0]
    assert "record count mismatch" in failures[1]


def test_current_roll_line_parser_rejects_invalid_epic_without_retaining_it() -> None:
    record = parse_voter_line(
        "3 | bad-id | Name: Test Person | Other: Test Relative | House: H-3 | Age: 40 | Gender: Other"
    )
    assert record is not None
    assert record["epic_number"] == ""
    assert record["data_quality"] == "invalid_epic_format"


def test_parser_registry_fails_closed_until_official_current_pdf_validation() -> None:
    spec = parser_spec("maharashtra_current_unicode_v1")
    assert spec.validation_status == "synthetic_fixture_only"
    assert spec.ingestion_ready is False
    with pytest.raises(ValueError, match="not ingestion-ready"):
        validate_parser_scope(
            spec.parser_hint,
            state_id="IN-MH",
            roll_kind="current_roll",
        )
    fixture_spec = validate_parser_scope(
        spec.parser_hint,
        state_id="IN-MH",
        roll_kind="current_roll",
        require_ready=False,
    )
    assert fixture_spec.parser_name == "maharashtra_current_unicode_v1"


def test_parser_registry_rejects_wrong_state_and_roll_kind() -> None:
    with pytest.raises(ValueError, match="not valid for state"):
        validate_parser_scope("parse_2002", state_id="IN-WB", roll_kind="historical_base_roll")
    with pytest.raises(ValueError, match="not valid for roll_kind"):
        validate_parser_scope("parse_2002", state_id="IN-MH", roll_kind="current_roll")
    with pytest.raises(ValueError, match="unsupported parser_hint"):
        parser_spec("unknown_parser")
