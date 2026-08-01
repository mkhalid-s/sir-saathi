"""Create and validate privacy-safe manual accessibility release evidence."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import re
from typing import Any

from .deployment_preflight import _public_origin
from .translation_catalog import DEFAULT_LOCALES_PATH, _load_json

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = 1
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
RESULTS = {"pass", "fail", "not_tested"}
CHECKS = (
    ("keyboard_navigation", "Keyboard-only guidance and official-check journey, visible focus, and skip link"),
    ("screen_reader_announcements", "Labels, disabled languages, updates, errors, busy states, and results"),
    ("zoom_and_reflow", "200% text, 400% page zoom, and 320 CSS-pixel reflow"),
    ("contrast_and_forced_colours", "Text/non-text contrast, focus, selected and disabled forced-colour states"),
    ("text_spacing", "WCAG text-spacing overrides without clipping or overlap"),
    ("target_size", "Interactive target-size review"),
    ("reduced_motion", "Reduced-motion behavior"),
    ("offline_and_api_failure", "Offline navigation and API failure focus/announcement behavior"),
    ("locale_language_direction", "Every publishable locale's language, direction, wrapping, and placeholders"),
    ("mixed_script_content", "Mixed-script names, numbers, punctuation, focus order, and external URLs"),
    ("long_content_small_viewport", "Long jurisdiction names and action labels at 200% text size"),
)
ENVIRONMENTS = (
    ("keyboard_desktop", "Desktop keyboard"),
    ("nvda_windows", "NVDA on Windows with Firefox or Chrome"),
    ("voiceover_apple", "VoiceOver with Safari on macOS or iOS"),
    ("talkback_android", "TalkBack with Chrome on Android"),
)


def create_template() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": "full_release",
        "deployed_commit": None,
        "deployed_origin": None,
        "reviewer": None,
        "review_date": None,
        "publishable_locales_tested": [],
        "privacy_attestation": False,
        "environments": [
            {
                "id": identifier,
                "label": label,
                "os": "",
                "os_version": "",
                "browser": "",
                "browser_version": "",
                "assistive_technology": "",
                "assistive_technology_version": "",
                "result": "not_tested",
                "evidence": "",
            }
            for identifier, label in ENVIRONMENTS
        ],
        "checks": [
            {
                "id": identifier,
                "label": label,
                "result": "not_tested",
                "evidence": "",
                "remediation": "",
                "retest_result": "not_tested",
            }
            for identifier, label in CHECKS
        ],
    }


def _publishable_locales(locales_path: Path) -> set[str]:
    locales = _load_json(locales_path).get("locales")
    if not isinstance(locales, list):
        raise ValueError("locale registry must contain a locales list")
    return {
        str(entry["code"])
        for entry in locales
        if isinstance(entry, dict) and entry.get("status") == "available" and isinstance(entry.get("code"), str)
    }


def _complete_text(value: Any, *, maximum: int = 1000) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= maximum


def validate_evidence(
    evidence: dict[str, Any],
    *,
    today: date | None = None,
    locales_path: Path = DEFAULT_LOCALES_PATH,
) -> dict[str, Any]:
    blockers: list[str] = []
    if evidence.get("schema_version") != SCHEMA_VERSION:
        blockers.append("evidence.schema_version")
    if evidence.get("scope") != "full_release":
        blockers.append("evidence.full_release_scope")
    commit = evidence.get("deployed_commit")
    if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
        blockers.append("evidence.deployed_commit")
    origin = evidence.get("deployed_origin")
    if not isinstance(origin, str) or not _public_origin(origin)[0]:
        blockers.append("evidence.deployed_https_origin")
    if not _complete_text(evidence.get("reviewer"), maximum=200):
        blockers.append("evidence.reviewer")
    try:
        reviewed_at = date.fromisoformat(evidence.get("review_date"))
        if reviewed_at > (today or date.today()):
            blockers.append("evidence.review_date_future")
    except (TypeError, ValueError):
        blockers.append("evidence.review_date")
    if evidence.get("privacy_attestation") is not True:
        blockers.append("evidence.privacy_attestation")

    expected_locales = _publishable_locales(locales_path)
    actual_locales = evidence.get("publishable_locales_tested")
    if not isinstance(actual_locales, list) or set(actual_locales) != expected_locales:
        blockers.append("evidence.publishable_locale_coverage")

    environments = evidence.get("environments")
    environment_by_id = {
        item.get("id"): item for item in environments if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(environments, list) else {}
    if set(environment_by_id) != {identifier for identifier, _label in ENVIRONMENTS}:
        blockers.append("evidence.environment_set")
    for identifier, _label in ENVIRONMENTS:
        item = environment_by_id.get(identifier)
        if not item:
            continue
        required_fields = ["os", "os_version", "browser", "browser_version", "evidence"]
        if identifier != "keyboard_desktop":
            required_fields += ["assistive_technology", "assistive_technology_version"]
        if item.get("result") != "pass" or any(not _complete_text(item.get(field)) for field in required_fields):
            blockers.append(f"environment.{identifier}")

    checks = evidence.get("checks")
    check_by_id = {
        item.get("id"): item for item in checks if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(checks, list) else {}
    if set(check_by_id) != {identifier for identifier, _label in CHECKS}:
        blockers.append("evidence.check_set")
    for identifier, _label in CHECKS:
        item = check_by_id.get(identifier)
        if not item:
            continue
        result = item.get("result")
        if result not in RESULTS:
            blockers.append(f"check.{identifier}.invalid_result")
        elif result == "pass":
            if not _complete_text(item.get("evidence")):
                blockers.append(f"check.{identifier}.missing_evidence")
        elif result == "fail":
            if not _complete_text(item.get("evidence")) or not _complete_text(item.get("remediation")):
                blockers.append(f"check.{identifier}.incomplete_failure")
            if item.get("retest_result") != "pass":
                blockers.append(f"check.{identifier}.retest_not_passed")
        else:
            blockers.append(f"check.{identifier}.not_tested")

    unique_blockers = list(dict.fromkeys(blockers))
    return {
        "ready_for_accessibility_signoff": not unique_blockers,
        "blockers": unique_blockers,
        "required_check_count": len(CHECKS),
        "required_environment_count": len(ENVIRONMENTS),
        "values_redacted": True,
    }


def _safe_output_path(output: Path) -> Path:
    resolved = output.resolve()
    if resolved == ROOT or (ROOT in resolved.parents and not any(
        resolved.is_relative_to((ROOT / directory).resolve()) for directory in ("reports", "data")
    )):
        raise ValueError("repository evidence templates must stay under ignored reports/ or data/")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create or validate manual accessibility release evidence.")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument("--create-template", action="store_true")
    actions.add_argument("--validate", type=Path, metavar="EVIDENCE")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--require-full-pass", action="store_true")
    args = parser.parse_args(argv)

    if args.create_template:
        if args.output is None:
            parser.error("--output is required with --create-template")
        try:
            output = _safe_output_path(args.output)
            if output.exists() and not args.replace:
                raise ValueError("output already exists; use --replace only after preserving prior evidence")
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(create_template(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps({"written": str(args.output), "ready_for_accessibility_signoff": False}, sort_keys=True))
        return 0

    if args.output is not None:
        parser.error("--output is only valid with --create-template")
    try:
        payload = _load_json(args.validate)
        report = validate_evidence(payload)
    except (OSError, json.JSONDecodeError, ValueError):
        report = {
            "ready_for_accessibility_signoff": False,
            "blockers": ["evidence.unreadable"],
            "required_check_count": len(CHECKS),
            "required_environment_count": len(ENVIRONMENTS),
            "values_redacted": True,
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.require_full_pass and not report["ready_for_accessibility_signoff"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
