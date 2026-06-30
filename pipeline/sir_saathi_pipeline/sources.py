"""Source manifest models for local-only ingestion runs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

RollKind = Literal[
    "historical_base_roll",
    "base_roll",
    "current_roll",
    "draft_roll",
    "final_roll",
    "supplement",
    "deletion",
]
ALLOWED_LOCAL_ROOTS = {"data", "samples"}


@dataclass(frozen=True)
class SourceManifest:
    state_id: str
    roll_year: int
    roll_kind: RollKind
    source_uri: str
    local_path: Path | None = None
    parser_hint: str | None = None
    language: str | None = None
    source_id: str = ""
    source_label: str = ""
    reviewed: bool = False
    notes: str = ""

    @property
    def is_local_only(self) -> bool:
        return self.local_path is not None


def parse_source_manifest(data: dict[str, Any]) -> SourceManifest:
    local_path = data.get("local_path")
    return SourceManifest(
        source_id=str(data["source_id"]),
        state_id=str(data["state_id"]),
        roll_year=int(data["roll_year"]),
        roll_kind=data["roll_kind"],
        source_label=str(data["source_label"]),
        source_uri=str(data["source_uri"]),
        local_path=Path(local_path) if local_path else None,
        parser_hint=data.get("parser_hint"),
        language=data.get("language"),
        reviewed=bool(data.get("reviewed", False)),
        notes=data.get("notes", ""),
    )


def load_source_manifests(path: str | Path) -> dict[str, SourceManifest]:
    manifest_path = Path(path)
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = data.get("sources")
    if not isinstance(entries, list):
        raise ValueError("source manifest must contain a sources list")
    manifests = [parse_source_manifest(entry) for entry in entries]
    return {manifest.source_id: manifest for manifest in manifests}


def source_manifest_blockers(manifest: SourceManifest) -> list[str]:
    blockers: list[str] = []
    if not manifest.reviewed:
        blockers.append("source manifest entry must be reviewed before ingestion")
    if manifest.roll_year <= 0:
        blockers.append("roll_year must be positive")
    if not manifest.source_label:
        blockers.append("source_label is required")
    if not manifest.source_uri:
        blockers.append("source_uri is required")
    if manifest.local_path is None:
        blockers.append("local_path is required for local ingestion")
    elif manifest.local_path.is_absolute():
        blockers.append("local_path must be repo-relative")
    elif manifest.local_path.parts and manifest.local_path.parts[0] not in ALLOWED_LOCAL_ROOTS:
        blockers.append("local_path must stay under ignored data/ or samples/ directories")
    if manifest.parser_hint != "parse_2002":
        blockers.append("parser_hint must be parse_2002 for the current local pipeline")
    if not manifest.language:
        blockers.append("language is required")
    return blockers


def validate_source_manifest(path: str | Path, source_id: str) -> dict[str, Any]:
    manifests = load_source_manifests(path)
    if source_id not in manifests:
        raise ValueError(f"unknown source_id: {source_id}")
    manifest = manifests[source_id]
    blockers = source_manifest_blockers(manifest)
    return {
        "local_only": True,
        "source_id": manifest.source_id,
        "state_id": manifest.state_id,
        "roll_year": manifest.roll_year,
        "roll_kind": manifest.roll_kind,
        "source_label": manifest.source_label,
        "source_uri": manifest.source_uri,
        "local_path": manifest.local_path.as_posix() if manifest.local_path else None,
        "parser_hint": manifest.parser_hint,
        "language": manifest.language,
        "reviewed": manifest.reviewed,
        "valid_for_ingestion": not blockers,
        "blockers": blockers,
    }


def failure_report(message: str) -> dict[str, Any]:
    return {
        "local_only": True,
        "valid_for_ingestion": False,
        "error": message,
        "blockers": [message],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a reviewed local source manifest entry.")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--source-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = validate_source_manifest(args.manifest, args.source_id)
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid_for_ingestion"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
