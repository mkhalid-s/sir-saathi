"""Create and validate private human-translation campaign bundles."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .translation_catalog import (
    DEFAULT_CATALOG_DIR,
    DEFAULT_LOCALES_PATH,
    REFERENCE_LOCALE,
    create_review_packet,
)

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_NAME = "campaign.json"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("translation campaign JSON must be an object")
    return value


def _safe_output_directory(output: Path, catalog_dir: Path) -> Path:
    resolved = output.resolve()
    forbidden_descendants = (
        catalog_dir.resolve(),
        (ROOT / "apps/web/public").resolve(),
        (ROOT / "apps/web/dist").resolve(),
    )
    if resolved == ROOT or any(
        resolved == path or resolved.is_relative_to(path) for path in forbidden_descendants
    ):
        raise ValueError("translation campaigns cannot be written to runtime or public directories")
    if resolved.is_relative_to(ROOT):
        allowed = tuple((ROOT / name).resolve() for name in ("data", "reports", "samples"))
        if not any(resolved.is_relative_to(path) for path in allowed):
            raise ValueError("repository translation campaigns must stay under ignored data/, reports/, or samples/")
    return resolved


def _planned_locales(locales_path: Path) -> list[dict[str, Any]]:
    registry = _load(locales_path)
    locales = registry.get("locales")
    if not isinstance(locales, list):
        raise ValueError("locale registry must contain a locales list")
    return sorted(
        (item for item in locales if isinstance(item, dict) and item.get("status") == "planned"),
        key=lambda item: item["code"],
    )


def campaign_manifest(
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> dict[str, Any]:
    planned = _planned_locales(locales_path)
    packets = [
        create_review_packet(item["code"], locales_path=locales_path, catalog_dir=catalog_dir)
        for item in planned
    ]
    if not packets:
        raise ValueError("translation campaign requires at least one planned locale")
    first = packets[0]
    return {
        "schema_version": 1,
        "source_locale": REFERENCE_LOCALE,
        "source_catalogue_sha256": first["source_catalogue_sha256"],
        "message_count": len(first["entries"]),
        "safety_critical_entry_count": first["review_requirements"]["safety_critical_entry_count"],
        "locale_count": len(packets),
        "human_translation_required": True,
        "independent_review_required": True,
        "locales": [
            {
                "code": packet["locale"],
                "label": packet["label"],
                "direction": packet["direction"],
                "packet": f"{packet['locale']}.json",
            }
            for packet in packets
        ],
    }


def create_campaign(
    output: Path,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> dict[str, Any]:
    destination = _safe_output_directory(output, catalog_dir)
    if destination.exists():
        raise ValueError("translation campaign output already exists; preserve review work and choose a new directory")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = campaign_manifest(locales_path=locales_path, catalog_dir=catalog_dir)
    with tempfile.TemporaryDirectory(prefix=".translation-campaign-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "bundle"
        staging.mkdir()
        for item in manifest["locales"]:
            packet = create_review_packet(
                item["code"], locales_path=locales_path, catalog_dir=catalog_dir
            )
            (staging / item["packet"]).write_text(
                json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        (staging / MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(staging, destination)
    return {
        "written": True,
        "locale_count": manifest["locale_count"],
        "message_count": manifest["message_count"],
        "values_redacted": True,
    }


def validate_campaign(
    directory: Path,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> dict[str, Any]:
    blockers: list[str] = []
    try:
        expected_manifest = campaign_manifest(locales_path=locales_path, catalog_dir=catalog_dir)
        actual_manifest = _load(directory / MANIFEST_NAME)
        if actual_manifest != expected_manifest:
            blockers.append("campaign.manifest_stale_or_invalid")
        expected_by_code = {item["code"]: item for item in expected_manifest["locales"]}
        for code, item in expected_by_code.items():
            try:
                actual = _load(directory / item["packet"])
                expected = create_review_packet(
                    code, locales_path=locales_path, catalog_dir=catalog_dir
                )
                for field in (
                    "schema_version", "locale", "label", "direction", "source_locale",
                    "source_catalogue_sha256", "review_requirements",
                ):
                    if actual.get(field) != expected[field]:
                        raise ValueError("packet metadata mismatch")
                actual_entries = actual.get("entries")
                if not isinstance(actual_entries, dict) or set(actual_entries) != set(expected["entries"]):
                    raise ValueError("packet entries mismatch")
                for key, expected_entry in expected["entries"].items():
                    actual_entry = actual_entries.get(key)
                    if not isinstance(actual_entry, dict) or any(
                        actual_entry.get(field) != expected_entry[field]
                        for field in ("source", "placeholders", "section", "risk")
                    ):
                        raise ValueError("packet source metadata mismatch")
            except (OSError, ValueError, json.JSONDecodeError):
                blockers.append(f"campaign.packet_invalid.{code}")
    except (OSError, ValueError, json.JSONDecodeError):
        blockers.append("campaign.invalid")
        expected_manifest = {"locale_count": 0, "message_count": 0}
    unique_blockers = sorted(set(blockers))
    return {
        "ready_for_human_translation": not unique_blockers,
        "locale_count": expected_manifest["locale_count"],
        "message_count": expected_manifest["message_count"],
        "blockers": unique_blockers,
        "values_redacted": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate a private translation campaign bundle.")
    parser.add_argument("--locales", type=Path, default=DEFAULT_LOCALES_PATH)
    parser.add_argument("--catalog-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--create", type=Path, metavar="OUTPUT_DIR")
    action.add_argument("--check", type=Path, metavar="CAMPAIGN_DIR")
    args = parser.parse_args(argv)
    try:
        if args.create:
            report = create_campaign(
                args.create, locales_path=args.locales, catalog_dir=args.catalog_dir
            )
        else:
            report = validate_campaign(
                args.check, locales_path=args.locales, catalog_dir=args.catalog_dir
            )
    except (OSError, ValueError, json.JSONDecodeError):
        report = {
            "ready_for_human_translation": False,
            "blockers": ["campaign.invalid"],
            "values_redacted": True,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report.get("blockers") else 0


if __name__ == "__main__":
    raise SystemExit(main())
