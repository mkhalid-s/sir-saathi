"""Fail-closed readiness checks for human-reviewed UI translation catalogues."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCALES_PATH = ROOT / "config" / "locales.json"
DEFAULT_CATALOG_DIR = ROOT / "config" / "translations"
REFERENCE_LOCALE = "en"
PLACEHOLDER_PATTERN = re.compile(r"\{([a-z][a-z0-9_]*)\}")


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _messages(catalog: dict[str, Any], *, path: Path) -> dict[str, str]:
    messages = catalog.get("messages")
    if not isinstance(messages, dict) or not messages:
        raise ValueError(f"{path} messages must be a non-empty object")
    if any(not isinstance(key, str) or not isinstance(value, str) or not value.strip() for key, value in messages.items()):
        raise ValueError(f"{path} messages must contain non-empty string keys and values")
    return messages


def validate_catalog(path: Path, *, locale: str, reference_messages: dict[str, str]) -> list[str]:
    """Return publish-blocking issues without exposing translated message content."""

    blockers: list[str] = []
    try:
        catalog = _load_json(path)
        messages = _messages(catalog, path=path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [str(exc)]

    if catalog.get("schema_version") != 1:
        blockers.append("unsupported translation schema_version")
    if catalog.get("locale") != locale:
        blockers.append("catalog locale does not match filename/registry locale")
    missing = sorted(set(reference_messages) - set(messages))
    extra = sorted(set(messages) - set(reference_messages))
    if missing:
        blockers.append(f"missing {len(missing)} message keys")
    if extra:
        blockers.append(f"contains {len(extra)} unknown message keys")
    for key in sorted(set(reference_messages) & set(messages)):
        expected = set(PLACEHOLDER_PATTERN.findall(reference_messages[key]))
        actual = set(PLACEHOLDER_PATTERN.findall(messages[key]))
        if expected != actual:
            blockers.append(f"placeholder mismatch for {key}")

    review = catalog.get("review")
    if locale == REFERENCE_LOCALE:
        if not isinstance(review, dict) or review.get("status") != "source":
            blockers.append("English reference catalogue must have source review status")
    else:
        if not isinstance(review, dict) or review.get("status") != "reviewed":
            blockers.append("fluent human review is required")
        else:
            reviewer = review.get("reviewed_by")
            reviewed_at = review.get("reviewed_at")
            if not isinstance(reviewer, str) or not reviewer.strip():
                blockers.append("reviewed_by is required")
            try:
                date.fromisoformat(reviewed_at)
            except (TypeError, ValueError):
                blockers.append("reviewed_at must be an ISO date")
    return blockers


def translation_readiness(
    *, locales_path: Path = DEFAULT_LOCALES_PATH, catalog_dir: Path = DEFAULT_CATALOG_DIR
) -> dict[str, Any]:
    locales_data = _load_json(locales_path)
    locales = locales_data.get("locales")
    if not isinstance(locales, list):
        raise ValueError("locale registry must contain a locales list")
    reference_path = catalog_dir / f"{REFERENCE_LOCALE}.json"
    reference_messages = _messages(_load_json(reference_path), path=reference_path)
    results: list[dict[str, Any]] = []
    for entry in locales:
        if not isinstance(entry, dict) or not isinstance(entry.get("code"), str):
            raise ValueError("each locale registry entry must have a string code")
        code = entry["code"]
        status = entry.get("status")
        path = catalog_dir / f"{code}.json"
        blockers = validate_catalog(path, locale=code, reference_messages=reference_messages) if path.exists() else ["catalogue file is missing"]
        initially_ready = not blockers
        if status == "available" and not initially_ready:
            blockers.append("registry marks locale available before catalogue readiness")
        if status == "planned" and initially_ready:
            blockers.append("reviewed catalogue is ready but registry still marks locale planned")
        results.append({
            "locale": code,
            "label": entry.get("label"),
            "registry_status": status,
            "catalogue_present": path.exists(),
            "message_count": len(reference_messages) if initially_ready else 0,
            "publishable": not blockers,
            "blockers": blockers,
        })
    return {
        "reference_locale": REFERENCE_LOCALE,
        "required_message_count": len(reference_messages),
        "locale_count": len(results),
        "available_locales": [item["locale"] for item in results if item["publishable"]],
        "locales": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report safe UI translation catalogue readiness.")
    parser.add_argument("--locales", type=Path, default=DEFAULT_LOCALES_PATH)
    parser.add_argument("--catalog-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    parser.add_argument("--fail-on-invalid-available", action="store_true")
    args = parser.parse_args(argv)
    report = translation_readiness(locales_path=args.locales, catalog_dir=args.catalog_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    invalid_available = any(
        item["registry_status"] == "available" and not item["publishable"] for item in report["locales"]
    )
    return 1 if args.fail_on_invalid_available and invalid_available else 0


if __name__ == "__main__":
    raise SystemExit(main())
