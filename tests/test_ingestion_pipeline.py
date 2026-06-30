import pytest

from pipeline.sir_saathi_pipeline.ingestion import (
    ParsedRollInput,
    SourceDocumentInput,
    build_ingestion_batch,
    epic_fingerprint,
    normalize_name,
)


def sample_roll(total_voters: int = 2) -> ParsedRollInput:
    return ParsedRollInput(
        state_id="IN-MH",
        roll_year=2002,
        roll_kind="historical_base_roll",
        language="mr",
        source_label="Synthetic pilot roll fixture",
        source_url="https://example.test/roll.pdf",
        parser_name="parse_2002",
        metadata={
            "ac_number": 172,
            "part_number": 21,
            "total_voters": total_voters,
            "ac_name_encoded": "Trombay",
            "ac_reservation_encoded": "general",
            "polling_station_name_encoded": "Pilot polling station",
        },
        voters=(
            {
                "serial_number": 1,
                "voter_name": "  Sample   Voter  ",
                "relation_type": "father",
                "relative_name": "Example Parent",
                "age": 41,
                "gender": "M",
                "epic_number": "sample-card-0001",
                "data_quality": "ok",
            },
            {
                "serial_number": 2,
                "voter_name": "Second Voter",
                "relation_type": "spouse",
                "relative_name": "Example Spouse",
                "age": 39,
                "gender": "F",
                "epic_number": "sample-card-0002",
                "data_quality": "missing_age,review",
            },
        ),
        source_document=SourceDocumentInput(
            state_id="IN-MH",
            source_uri="local://synthetic/pilot-roll.pdf",
            local_path="data/local/pilot-roll.pdf",
            checksum="sha256:syntheticchecksum",
            parser_hint="parse_2002",
        ),
    )


def test_build_ingestion_batch_maps_parsed_roll_to_db_rows() -> None:
    batch = build_ingestion_batch(sample_roll(), hash_salt="unit-test-salt")

    assert batch.roll_version["state_id"] == "IN-MH"
    assert batch.roll_version["roll_year"] == 2002
    assert batch.source_document["status"] == "registered"
    assert batch.assembly_constituency["ac_number"] == 172
    assert batch.polling_station["part_number"] == 21
    assert batch.extraction_run["status"] == "validated"
    assert batch.extraction_run["expected_records"] == 2
    assert batch.extraction_run["parsed_records"] == 2
    assert batch.extraction_run["quality_summary"] == {"ok": 1, "missing_age": 1, "review": 1}

    first = batch.voter_records[0]
    assert first["name_original"] == "  Sample   Voter  "
    assert first["name_normalized"] == "sample voter"
    assert first["relative_name_normalized"] == "example parent"
    assert first["epic_hash"] is not None
    assert first["epic_last4"] == "0001"
    assert "sample-card" not in first.values()


def test_build_ingestion_batch_rejects_count_mismatch() -> None:
    with pytest.raises(ValueError, match="parsed record count mismatch"):
        build_ingestion_batch(sample_roll(total_voters=3), hash_salt="unit-test-salt")


def test_build_ingestion_batch_requires_source_provenance() -> None:
    roll = sample_roll()
    broken = ParsedRollInput(
        state_id=roll.state_id,
        roll_year=roll.roll_year,
        roll_kind=roll.roll_kind,
        language=roll.language,
        source_label=roll.source_label,
        parser_name=roll.parser_name,
        metadata=roll.metadata,
        voters=roll.voters,
        source_url=roll.source_url,
        source_document=SourceDocumentInput(
            state_id="IN-MH",
            source_uri="",
            checksum="",
            parser_hint="parse_2002",
        ),
    )
    with pytest.raises(ValueError, match="checksum"):
        build_ingestion_batch(broken, hash_salt="unit-test-salt")


def test_ingestion_helpers_normalize_and_fingerprint_without_raw_identifier() -> None:
    assert normalize_name("  Mixed   CASE  Name ") == "mixed case name"
    first_hash, first_last4 = epic_fingerprint("sample-card-0001", hash_salt="unit-test-salt")
    second_hash, second_last4 = epic_fingerprint("sample-card-0001", hash_salt="other-salt")
    assert first_last4 == "0001"
    assert first_hash != second_hash
    assert "sample-card" not in first_hash
