"""Source manifest models for local-only ingestion runs."""

from __future__ import annotations

import argparse
import hashlib
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
CHECKSUM_PREFIX = "sha256:"


@dataclass(frozen=True)
class SourceManifest:
    state_id: str
    roll_year: int
    roll_kind: RollKind
    source_uri: str
    local_path: Path | None = None
    parser_hint: str | None = None
    language: str | None = None
    checksum: str = ""
    source_id: str = ""
    source_label: str = ""
    reviewed: bool = False
    notes: str = ""

    @property
    def is_local_only(self) -> bool:
        return self.local_path is not None


@dataclass(frozen=True)
class DraftSourceManifestRequest:
    source_id: str
    state_id: str
    roll_year: int
    roll_kind: RollKind
    source_label: str
    source_uri: str
    local_path: Path
    language: str
    parser_hint: str = "parse_2002"
    notes: str = ""


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
        checksum=str(data.get("checksum", "")),
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


def is_sha256_checksum(value: str) -> bool:
    if not value.startswith(CHECKSUM_PREFIX):
        return False
    digest = value.removeprefix(CHECKSUM_PREFIX)
    return len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)


def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"{CHECKSUM_PREFIX}{digest.hexdigest()}"


def require_repo_relative_local_path(path: Path) -> Path:
    if path.is_absolute():
        raise ValueError("local_path must be repo-relative")
    if not path.parts or path.parts[0] not in ALLOWED_LOCAL_ROOTS:
        raise ValueError("local_path must stay under ignored data/ or samples/ directories")
    return path


def require_repo_relative_manifest_path(path: Path) -> Path:
    if path.is_absolute():
        raise ValueError("manifest path must be repo-relative")
    if not path.parts or path.parts[0] not in ALLOWED_LOCAL_ROOTS:
        raise ValueError("manifest path must stay under ignored data/ or samples/ directories")
    return path


def draft_source_manifest_entry(
    request: DraftSourceManifestRequest,
    *,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    local_path = require_repo_relative_local_path(request.local_path)
    pdf_path = Path(repo_root) / local_path
    if not pdf_path.exists():
        raise ValueError("local_path file does not exist for manifest drafting")
    checksum = compute_sha256(pdf_path)
    entry = {
        "source_id": request.source_id,
        "state_id": request.state_id,
        "roll_year": request.roll_year,
        "roll_kind": request.roll_kind,
        "source_label": request.source_label,
        "source_uri": request.source_uri,
        "local_path": local_path.as_posix(),
        "checksum": checksum,
        "parser_hint": request.parser_hint,
        "language": request.language,
        "reviewed": False,
        "notes": request.notes or "TODO: human source review required before ingestion",
    }
    return {
        "local_only": True,
        "ready_for_review": True,
        "valid_for_ingestion": False,
        "review_required": True,
        "entry": entry,
        "next_step": "Review the source metadata, then set reviewed to true before ingestion.",
    }


def load_source_manifest_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"sources": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("sources"), list):
        raise ValueError("source manifest must contain a sources list")
    return data


def write_draft_source_manifest_entry(
    request: DraftSourceManifestRequest,
    *,
    manifest_path: Path,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    relative_manifest_path = require_repo_relative_manifest_path(manifest_path)
    resolved_manifest_path = Path(repo_root) / relative_manifest_path
    draft = draft_source_manifest_entry(request, repo_root=repo_root)
    document = load_source_manifest_document(resolved_manifest_path)
    entry = draft["entry"]
    if any(existing.get("source_id") == entry["source_id"] for existing in document["sources"]):
        raise ValueError(f"source_id already exists in manifest: {entry['source_id']}")
    document["sources"].append(entry)
    resolved_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_manifest_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **draft,
        "manifest_path": relative_manifest_path.as_posix(),
        "wrote_manifest": True,
        "source_count": len(document["sources"]),
    }


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
    if not is_sha256_checksum(manifest.checksum):
        blockers.append("checksum must be sha256:<64 lowercase hex>")
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


def source_file_blockers(manifest: SourceManifest, *, repo_root: Path) -> list[str]:
    if manifest.local_path is None:
        return ["local_path is required for checksum verification"]
    pdf_path = repo_root / manifest.local_path
    if not pdf_path.exists():
        return ["local_path file does not exist for checksum verification"]
    actual_checksum = compute_sha256(pdf_path)
    if actual_checksum != manifest.checksum:
        return ["local file checksum does not match source manifest"]
    return []


def validate_source_manifest(
    path: str | Path,
    source_id: str,
    *,
    verify_file: bool = False,
    repo_root: str | Path = ".",
) -> dict[str, Any]:
    manifests = load_source_manifests(path)
    if source_id not in manifests:
        raise ValueError(f"unknown source_id: {source_id}")
    manifest = manifests[source_id]
    blockers = source_manifest_blockers(manifest)
    file_blockers = source_file_blockers(manifest, repo_root=Path(repo_root)) if verify_file else []
    blockers.extend(file_blockers)
    return {
        "local_only": True,
        "source_id": manifest.source_id,
        "state_id": manifest.state_id,
        "roll_year": manifest.roll_year,
        "roll_kind": manifest.roll_kind,
        "source_label": manifest.source_label,
        "source_uri": manifest.source_uri,
        "local_path": manifest.local_path.as_posix() if manifest.local_path else None,
        "checksum": manifest.checksum,
        "parser_hint": manifest.parser_hint,
        "language": manifest.language,
        "reviewed": manifest.reviewed,
        "checksum_verified": verify_file and not file_blockers,
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
    parser.add_argument("--draft", action="store_true", help="Draft a reviewed:false manifest entry with a computed checksum.")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-id")
    parser.add_argument("--verify-file", action="store_true", help="Hash the local ignored PDF and compare it with the manifest checksum.")
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root used to resolve manifest local_path.")
    parser.add_argument("--state", help="Canonical state id for draft entries.")
    parser.add_argument("--roll-year", type=int, help="Roll year for draft entries.")
    parser.add_argument("--roll-kind", default="historical_base_roll", help="Roll kind for draft entries.")
    parser.add_argument("--source-label", help="Human-readable source label for draft entries.")
    parser.add_argument("--source-uri", help="Official source URI for draft entries.")
    parser.add_argument("--local-path", type=Path, help="Repo-relative local PDF path under ignored data/ or samples/.")
    parser.add_argument("--output-manifest", type=Path, help="Repo-relative manifest path to append a draft entry to.")
    parser.add_argument("--language", help="Roll language code for draft entries.")
    parser.add_argument("--parser-hint", default="parse_2002", help="Parser hint for draft entries.")
    parser.add_argument("--notes", default="", help="Optional review notes for draft entries.")
    return parser


def _require_arg(value: Any, name: str) -> Any:
    if value in (None, ""):
        raise ValueError(f"{name} is required")
    return value


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.draft:
            request = DraftSourceManifestRequest(
                source_id=_require_arg(args.source_id, "--source-id"),
                state_id=_require_arg(args.state, "--state"),
                roll_year=_require_arg(args.roll_year, "--roll-year"),
                roll_kind=args.roll_kind,
                source_label=_require_arg(args.source_label, "--source-label"),
                source_uri=_require_arg(args.source_uri, "--source-uri"),
                local_path=_require_arg(args.local_path, "--local-path"),
                language=_require_arg(args.language, "--language"),
                parser_hint=args.parser_hint,
                notes=args.notes,
            )
            if args.output_manifest:
                report = write_draft_source_manifest_entry(
                    request,
                    manifest_path=args.output_manifest,
                    repo_root=args.repo_root,
                )
            else:
                report = draft_source_manifest_entry(request, repo_root=args.repo_root)
        else:
            if args.output_manifest:
                raise ValueError("--output-manifest can only be used with --draft")
            report = validate_source_manifest(
                _require_arg(args.manifest, "--manifest"),
                _require_arg(args.source_id, "--source-id"),
                verify_file=args.verify_file,
                repo_root=args.repo_root,
            )
    except Exception as exc:
        print(json.dumps(failure_report(str(exc)), indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    if report.get("ready_for_review"):
        return 0
    return 0 if report["valid_for_ingestion"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
