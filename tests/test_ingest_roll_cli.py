import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline import ingest_roll


def write_pdf_placeholder(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "pilot.pdf"
    pdf_path.write_bytes(b"synthetic pdf bytes")
    return pdf_path


def synthetic_parser(_pdf_path: Path):
    return (
        {
            "revision_year": 2002,
            "ac_number": 172,
            "part_number": 21,
            "total_voters": 2,
            "ac_name_encoded": "Trombay",
            "ac_reservation_encoded": "general",
            "polling_station_name_encoded": "Pilot polling station",
        },
        [
            {
                "serial_number": 1,
                "voter_name": "Sample Voter",
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
        ],
        [],
    )


def mismatch_parser(_pdf_path: Path):
    metadata, voters, failures = synthetic_parser(_pdf_path)
    metadata = dict(metadata)
    metadata["total_voters"] = 3
    return metadata, voters, failures


def failing_parser(_pdf_path: Path):
    metadata, voters, _failures = synthetic_parser(_pdf_path)
    return metadata, voters, ["page 2 failed"]


def test_compute_sha256_returns_prefixed_digest(tmp_path: Path) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    assert ingest_roll.compute_sha256(pdf_path).startswith("sha256:")
    assert len(ingest_roll.compute_sha256(pdf_path)) == len("sha256:") + 64


def test_parsed_roll_from_pdf_adapts_parser_output(tmp_path: Path) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    parsed = ingest_roll.parsed_roll_from_pdf(
        pdf_path,
        state_id="IN-MH",
        roll_year=None,
        roll_kind="historical_base_roll",
        language="mr",
        source_label="Synthetic source",
        source_url=None,
        parser_fn=synthetic_parser,
    )

    assert parsed.roll_year == 2002
    assert parsed.metadata["ac_number"] == 172
    assert parsed.source_document.checksum.startswith("sha256:")
    assert parsed.source_document.source_uri.startswith("local://")
    assert len(parsed.voters) == 2


def test_run_dry_run_reports_safe_counts_without_raw_epic(tmp_path: Path) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    report = ingest_roll.run_dry_run(
        pdf_path,
        state_id="IN-MH",
        hash_salt="unit-test-salt",
        parser_fn=synthetic_parser,
    )
    encoded = json.dumps(report)

    assert report["safe_to_load"] is True
    assert report["expected_records"] == 2
    assert report["parsed_records"] == 2
    assert report["row_counts"]["voter_records"] == 2
    assert report["quality_summary"] == {"ok": 1, "missing_age": 1, "review": 1}
    assert "sample-card" not in encoded
    assert "voter_name" not in encoded


def test_run_dry_run_requires_hash_salt(tmp_path: Path) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    with pytest.raises(ValueError, match=ingest_roll.EPIC_HASH_SALT_ENV):
        ingest_roll.run_dry_run(
            pdf_path,
            state_id="IN-MH",
            hash_salt="",
            parser_fn=synthetic_parser,
        )


def test_main_fails_closed_when_dry_run_flag_is_missing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    exit_code = ingest_roll.main(["--pdf", str(pdf_path), "--state", "IN-MH"], parser_fn=synthetic_parser)
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 2
    assert output["safe_to_load"] is False
    assert "--dry-run is required" in output["error"]


def test_main_returns_failed_report_on_count_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    monkeypatch.setenv(ingest_roll.EPIC_HASH_SALT_ENV, "unit-test-salt")

    exit_code = ingest_roll.main(
        ["--pdf", str(pdf_path), "--state", "IN-MH", "--dry-run"],
        parser_fn=mismatch_parser,
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["safe_to_load"] is False
    assert "parsed record count mismatch" in output["error"]


def test_main_returns_failed_report_on_parser_failures(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pdf_path = write_pdf_placeholder(tmp_path)
    monkeypatch.setenv(ingest_roll.EPIC_HASH_SALT_ENV, "unit-test-salt")

    exit_code = ingest_roll.main(
        ["--pdf", str(pdf_path), "--state", "IN-MH", "--dry-run"],
        parser_fn=failing_parser,
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["safe_to_load"] is False
    assert "parser reported 1 failure" in output["error"]
