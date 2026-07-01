import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline import sources

VALID_CHECKSUM = "sha256:" + "a" * 64


def write_manifest(
    tmp_path: Path,
    *,
    reviewed: bool = True,
    local_path: str = "data/local/pilot.pdf",
    checksum: str = VALID_CHECKSUM,
) -> Path:
    manifest_path = tmp_path / "sources.json"
    manifest_path.write_text(
        json.dumps(
            {
                "sources": [
                    {
                        "source_id": "mh-2002-ac172-part21",
                        "state_id": "IN-MH",
                        "roll_year": 2002,
                        "roll_kind": "historical_base_roll",
                        "source_label": "Synthetic reviewed source",
                        "source_uri": "https://example.test/official.pdf",
                        "local_path": local_path,
                        "parser_hint": "parse_2002",
                        "language": "mr",
                        "checksum": checksum,
                        "reviewed": reviewed,
                        "notes": "synthetic test manifest",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return manifest_path


def test_load_source_manifests_parses_reviewed_entries(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)

    manifests = sources.load_source_manifests(manifest_path)
    manifest = manifests["mh-2002-ac172-part21"]

    assert manifest.state_id == "IN-MH"
    assert manifest.roll_year == 2002
    assert manifest.roll_kind == "historical_base_roll"
    assert manifest.local_path == Path("data/local/pilot.pdf")
    assert manifest.checksum == VALID_CHECKSUM
    assert manifest.is_local_only is True
    assert manifest.reviewed is True


def test_validate_source_manifest_returns_safe_report(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)

    report = sources.validate_source_manifest(manifest_path, "mh-2002-ac172-part21")
    encoded = json.dumps(report)

    assert report["local_only"] is True
    assert report["valid_for_ingestion"] is True
    assert report["blockers"] == []
    assert report["local_path"] == "data/local/pilot.pdf"
    assert report["checksum"] == VALID_CHECKSUM
    assert report["checksum_verified"] is False
    assert "voter_name" not in encoded
    assert "epic" not in encoded.casefold()


def test_source_manifest_blockers_require_reviewed_local_source(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path, reviewed=False, local_path="docs/pilot.pdf", checksum="bad")
    manifest = sources.load_source_manifests(manifest_path)["mh-2002-ac172-part21"]

    blockers = sources.source_manifest_blockers(manifest)

    assert "source manifest entry must be reviewed before ingestion" in blockers
    assert "local_path must stay under ignored data/ or samples/ directories" in blockers
    assert "checksum must be sha256:<64 lowercase hex>" in blockers


def test_validate_source_manifest_can_verify_local_file_checksum(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")
    manifest_path = write_manifest(tmp_path, checksum=sources.compute_sha256(pdf_path))

    report = sources.validate_source_manifest(
        manifest_path,
        "mh-2002-ac172-part21",
        verify_file=True,
        repo_root=tmp_path,
    )

    assert report["valid_for_ingestion"] is True
    assert report["checksum_verified"] is True
    assert report["blockers"] == []


def test_validate_source_manifest_rejects_checksum_mismatch(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"different bytes")
    manifest_path = write_manifest(tmp_path)

    report = sources.validate_source_manifest(
        manifest_path,
        "mh-2002-ac172-part21",
        verify_file=True,
        repo_root=tmp_path,
    )

    assert report["valid_for_ingestion"] is False
    assert "local file checksum does not match source manifest" in report["blockers"]


def test_draft_source_manifest_entry_computes_checksum_and_requires_review(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")

    report = sources.draft_source_manifest_entry(
        sources.DraftSourceManifestRequest(
            source_id="mh-2002-ac172-part21",
            state_id="IN-MH",
            roll_year=2002,
            roll_kind="historical_base_roll",
            source_label="Synthetic reviewed source",
            source_uri="https://example.test/official.pdf",
            local_path=Path("data/local/pilot.pdf"),
            language="mr",
        ),
        repo_root=tmp_path,
    )
    encoded = json.dumps(report)

    assert report["local_only"] is True
    assert report["ready_for_review"] is True
    assert report["valid_for_ingestion"] is False
    assert report["entry"]["reviewed"] is False
    assert report["entry"]["checksum"] == sources.compute_sha256(pdf_path)
    assert report["entry"]["local_path"] == "data/local/pilot.pdf"
    assert str(tmp_path) not in encoded
    assert "synthetic pdf bytes" not in encoded


def test_draft_source_manifest_rejects_paths_outside_ignored_roots(tmp_path: Path) -> None:
    pdf_path = tmp_path / "docs/pilot.pdf"
    pdf_path.parent.mkdir()
    pdf_path.write_bytes(b"synthetic pdf bytes")

    with pytest.raises(ValueError, match="ignored data/ or samples"):
        sources.draft_source_manifest_entry(
            sources.DraftSourceManifestRequest(
                source_id="mh-2002-ac172-part21",
                state_id="IN-MH",
                roll_year=2002,
                roll_kind="historical_base_roll",
                source_label="Synthetic reviewed source",
                source_uri="https://example.test/official.pdf",
                local_path=Path("docs/pilot.pdf"),
                language="mr",
            ),
            repo_root=tmp_path,
        )


def test_write_draft_source_manifest_entry_creates_local_manifest(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")

    report = sources.write_draft_source_manifest_entry(
        sources.DraftSourceManifestRequest(
            source_id="mh-2002-ac172-part21",
            state_id="IN-MH",
            roll_year=2002,
            roll_kind="historical_base_roll",
            source_label="Synthetic reviewed source",
            source_uri="https://example.test/official.pdf",
            local_path=Path("data/local/pilot.pdf"),
            language="mr",
        ),
        manifest_path=Path("data/local/sources.json"),
        repo_root=tmp_path,
    )
    manifest = json.loads((tmp_path / "data/local/sources.json").read_text(encoding="utf-8"))
    encoded = json.dumps(report)

    assert report["wrote_manifest"] is True
    assert report["valid_for_ingestion"] is False
    assert report["manifest_path"] == "data/local/sources.json"
    assert report["source_count"] == 1
    assert manifest["sources"][0]["reviewed"] is False
    assert manifest["sources"][0]["checksum"] == sources.compute_sha256(pdf_path)
    assert str(tmp_path) not in encoded


def test_write_draft_source_manifest_entry_rejects_duplicate_source_id(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")
    request = sources.DraftSourceManifestRequest(
        source_id="mh-2002-ac172-part21",
        state_id="IN-MH",
        roll_year=2002,
        roll_kind="historical_base_roll",
        source_label="Synthetic reviewed source",
        source_uri="https://example.test/official.pdf",
        local_path=Path("data/local/pilot.pdf"),
        language="mr",
    )
    sources.write_draft_source_manifest_entry(
        request,
        manifest_path=Path("data/local/sources.json"),
        repo_root=tmp_path,
    )

    with pytest.raises(ValueError, match="source_id already exists"):
        sources.write_draft_source_manifest_entry(
            request,
            manifest_path=Path("data/local/sources.json"),
            repo_root=tmp_path,
        )


def test_write_draft_source_manifest_rejects_manifest_outside_ignored_roots(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")

    with pytest.raises(ValueError, match="manifest path must stay under ignored data/ or samples"):
        sources.write_draft_source_manifest_entry(
            sources.DraftSourceManifestRequest(
                source_id="mh-2002-ac172-part21",
                state_id="IN-MH",
                roll_year=2002,
                roll_kind="historical_base_roll",
                source_label="Synthetic reviewed source",
                source_uri="https://example.test/official.pdf",
                local_path=Path("data/local/pilot.pdf"),
                language="mr",
            ),
            manifest_path=Path("docs/sources.json"),
            repo_root=tmp_path,
        )


def test_source_manifest_review_report_marks_complete_draft_ready_for_human_review(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")
    manifest_path = write_manifest(tmp_path, reviewed=False, checksum=sources.compute_sha256(pdf_path))

    report = sources.source_manifest_review_report(
        manifest_path,
        "mh-2002-ac172-part21",
        verify_file=True,
        repo_root=tmp_path,
    )
    checklist = {item["id"]: item["passed"] for item in report["checklist"]}

    assert report["local_only"] is True
    assert report["ready_for_human_review"] is True
    assert report["valid_for_ingestion"] is False
    assert report["review_required"] is True
    assert report["checksum_verified"] is True
    assert report["blockers"] == []
    assert checklist["human_review"] is False
    assert checklist["checksum_verified"] is True


def test_source_manifest_review_report_marks_reviewed_entry_valid_for_ingestion(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")
    manifest_path = write_manifest(tmp_path, reviewed=True, checksum=sources.compute_sha256(pdf_path))

    report = sources.source_manifest_review_report(
        manifest_path,
        "mh-2002-ac172-part21",
        verify_file=True,
        repo_root=tmp_path,
    )

    assert report["ready_for_human_review"] is False
    assert report["valid_for_ingestion"] is True
    assert report["review_required"] is False
    assert report["blockers"] == []


def test_source_manifest_review_report_returns_field_and_file_blockers(tmp_path: Path) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"different bytes")
    manifest_path = write_manifest(tmp_path, reviewed=False, checksum="bad")

    report = sources.source_manifest_review_report(
        manifest_path,
        "mh-2002-ac172-part21",
        verify_file=True,
        repo_root=tmp_path,
    )

    assert report["ready_for_human_review"] is False
    assert report["valid_for_ingestion"] is False
    assert "checksum must be sha256:<64 lowercase hex>" in report["blockers"]
    assert "local file checksum does not match source manifest" in report["blockers"]


def test_source_manifest_rejects_unknown_source_id(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path)

    with pytest.raises(ValueError, match="unknown source_id"):
        sources.validate_source_manifest(manifest_path, "missing")


def test_main_returns_nonzero_for_unreviewed_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = write_manifest(tmp_path, reviewed=False)

    exit_code = sources.main(["--manifest", str(manifest_path), "--source-id", "mh-2002-ac172-part21"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["valid_for_ingestion"] is False
    assert "source manifest entry must be reviewed before ingestion" in output["blockers"]


def test_main_returns_zero_for_valid_manifest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    manifest_path = write_manifest(tmp_path)

    exit_code = sources.main(["--manifest", str(manifest_path), "--source-id", "mh-2002-ac172-part21"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["valid_for_ingestion"] is True
    assert output["source_id"] == "mh-2002-ac172-part21"


def test_main_verifies_file_when_requested(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")
    manifest_path = write_manifest(tmp_path, checksum=sources.compute_sha256(pdf_path))

    exit_code = sources.main([
        "--manifest", str(manifest_path),
        "--source-id", "mh-2002-ac172-part21",
        "--verify-file",
        "--repo-root", str(tmp_path),
    ])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["checksum_verified"] is True


def test_main_drafts_manifest_entry_without_marking_reviewed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")

    exit_code = sources.main([
        "--draft",
        "--source-id", "mh-2002-ac172-part21",
        "--state", "IN-MH",
        "--roll-year", "2002",
        "--roll-kind", "historical_base_roll",
        "--source-label", "Synthetic reviewed source",
        "--source-uri", "https://example.test/official.pdf",
        "--local-path", "data/local/pilot.pdf",
        "--language", "mr",
        "--repo-root", str(tmp_path),
    ])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["ready_for_review"] is True
    assert output["valid_for_ingestion"] is False
    assert output["entry"]["reviewed"] is False
    assert output["entry"]["checksum"] == sources.compute_sha256(pdf_path)


def test_main_writes_draft_manifest_entry_without_marking_reviewed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")

    exit_code = sources.main([
        "--draft",
        "--source-id", "mh-2002-ac172-part21",
        "--state", "IN-MH",
        "--roll-year", "2002",
        "--roll-kind", "historical_base_roll",
        "--source-label", "Synthetic reviewed source",
        "--source-uri", "https://example.test/official.pdf",
        "--local-path", "data/local/pilot.pdf",
        "--language", "mr",
        "--output-manifest", "data/local/sources.json",
        "--repo-root", str(tmp_path),
    ])
    output = json.loads(capsys.readouterr().out)
    manifest = json.loads((tmp_path / "data/local/sources.json").read_text(encoding="utf-8"))

    assert exit_code == 0
    assert output["wrote_manifest"] is True
    assert output["valid_for_ingestion"] is False
    assert manifest["sources"][0]["reviewed"] is False
    assert manifest["sources"][0]["source_id"] == "mh-2002-ac172-part21"


def test_main_reports_source_manifest_review_status(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    pdf_path = tmp_path / "data/local/pilot.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"synthetic pdf bytes")
    manifest_path = write_manifest(tmp_path, reviewed=False, checksum=sources.compute_sha256(pdf_path))

    exit_code = sources.main([
        "--review",
        "--manifest", str(manifest_path),
        "--source-id", "mh-2002-ac172-part21",
        "--verify-file",
        "--repo-root", str(tmp_path),
    ])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert output["ready_for_human_review"] is True
    assert output["valid_for_ingestion"] is False
    assert output["review_required"] is True
