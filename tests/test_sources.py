import json
from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline import sources


def write_manifest(tmp_path: Path, *, reviewed: bool = True, local_path: str = "data/local/pilot.pdf") -> Path:
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
    assert "voter_name" not in encoded
    assert "epic" not in encoded.casefold()


def test_source_manifest_blockers_require_reviewed_local_source(tmp_path: Path) -> None:
    manifest_path = write_manifest(tmp_path, reviewed=False, local_path="docs/pilot.pdf")
    manifest = sources.load_source_manifests(manifest_path)["mh-2002-ac172-part21"]

    blockers = sources.source_manifest_blockers(manifest)

    assert "source manifest entry must be reviewed before ingestion" in blockers
    assert "local_path must stay under ignored data/ or samples/ directories" in blockers


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
