"""Fail-closed readiness checks for human-reviewed UI translation catalogues."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
from html import escape
import json
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCALES_PATH = ROOT / "config" / "locales.json"
DEFAULT_CATALOG_DIR = ROOT / "config" / "translations"
REFERENCE_LOCALE = "en"
PLACEHOLDER_PATTERN = re.compile(r"\{([a-z][a-z0-9_]*)\}")
REVIEW_PACKET_SCHEMA_VERSION = 2
SAFETY_CRITICAL_PREFIXES = (
    "document.",
    "find.",
    "forms.",
    "guidance.",
    "safety.",
    "search.",
    "state.schedule.",
    "status.",
    "wizard.",
)


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


def _source_digest(messages: dict[str, str]) -> str:
    canonical = json.dumps(messages, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _locale_entry(locales_path: Path, locale: str) -> dict[str, Any]:
    locales = _load_json(locales_path).get("locales")
    if not isinstance(locales, list):
        raise ValueError("locale registry must contain a locales list")
    matches = [entry for entry in locales if isinstance(entry, dict) and entry.get("code") == locale]
    if len(matches) != 1:
        raise ValueError(f"locale registry must contain exactly one {locale} entry")
    return matches[0]


def _review_risk(key: str) -> str:
    return "safety_critical" if key.startswith(SAFETY_CRITICAL_PREFIXES) else "standard"


def create_review_packet(
    locale: str,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> dict[str, Any]:
    """Create a non-publishable, source-pinned packet for a fluent translator."""

    if locale == REFERENCE_LOCALE:
        raise ValueError("the English source catalogue does not need a translation review packet")
    locale_entry = _locale_entry(locales_path, locale)
    reference_path = catalog_dir / f"{REFERENCE_LOCALE}.json"
    reference_messages = _messages(_load_json(reference_path), path=reference_path)
    critical_count = sum(_review_risk(key) == "safety_critical" for key in reference_messages)
    return {
        "schema_version": REVIEW_PACKET_SCHEMA_VERSION,
        "locale": locale,
        "label": locale_entry.get("label"),
        "direction": locale_entry.get("direction"),
        "source_locale": REFERENCE_LOCALE,
        "source_catalogue_sha256": _source_digest(reference_messages),
        "review_requirements": {
            "distinct_translator_and_reviewer": True,
            "safety_critical_entry_count": critical_count,
            "preserve_placeholders_exactly": True,
        },
        "review": {
            "status": "draft",
            "translated_by": None,
            "reviewed_by": None,
            "reviewed_at": None,
        },
        "entries": {
            key: {
                "source": value,
                "translation": "",
                "placeholders": sorted(set(PLACEHOLDER_PATTERN.findall(value))),
                "section": key.split(".", 1)[0],
                "risk": _review_risk(key),
            }
            for key, value in sorted(reference_messages.items())
        },
    }


def _validated_packet_content(
    packet_path: Path,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> tuple[dict[str, Any], str, dict[str, Any], dict[str, str]]:
    """Validate source pinning, metadata, translations, and placeholders without approving publication."""

    packet = _load_json(packet_path)
    if packet.get("schema_version") != REVIEW_PACKET_SCHEMA_VERSION:
        raise ValueError("unsupported review packet schema_version; create a fresh review packet")
    locale = packet.get("locale")
    if not isinstance(locale, str) or not locale or locale == REFERENCE_LOCALE:
        raise ValueError("review packet must name a registered non-English locale")
    locale_entry = _locale_entry(locales_path, locale)
    if packet.get("direction") != locale_entry.get("direction"):
        raise ValueError("review packet direction does not match the locale registry")

    reference_path = catalog_dir / f"{REFERENCE_LOCALE}.json"
    reference_messages = _messages(_load_json(reference_path), path=reference_path)
    if packet.get("source_catalogue_sha256") != _source_digest(reference_messages):
        raise ValueError("review packet is stale; create it again from the current English catalogue")
    expected_critical_count = sum(_review_risk(key) == "safety_critical" for key in reference_messages)
    requirements = packet.get("review_requirements")
    if requirements != {
        "distinct_translator_and_reviewer": True,
        "safety_critical_entry_count": expected_critical_count,
        "preserve_placeholders_exactly": True,
    }:
        raise ValueError("review packet requirements do not match the current review policy")

    entries = packet.get("entries")
    if not isinstance(entries, dict) or set(entries) != set(reference_messages):
        raise ValueError("review packet keys do not match the current English catalogue")
    translated: dict[str, str] = {}
    for key, source in reference_messages.items():
        entry = entries.get(key)
        if not isinstance(entry, dict) or entry.get("source") != source:
            raise ValueError(f"source text mismatch for {key}")
        expected_placeholders = sorted(set(PLACEHOLDER_PATTERN.findall(source)))
        if (
            entry.get("section") != key.split(".", 1)[0]
            or entry.get("risk") != _review_risk(key)
            or entry.get("placeholders") != expected_placeholders
        ):
            raise ValueError(f"review metadata mismatch for {key}")
        translation = entry.get("translation")
        if not isinstance(translation, str) or not translation.strip():
            raise ValueError(f"translation is required for {key}")
        expected = set(expected_placeholders)
        actual = set(PLACEHOLDER_PATTERN.findall(translation))
        if expected != actual:
            raise ValueError(f"placeholder mismatch for {key}")
        translated[key] = translation
    return packet, locale, locale_entry, translated


def compile_reviewed_packet(
    packet_path: Path,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> dict[str, Any]:
    """Validate a completed human-review packet and return a runtime catalogue."""

    packet, locale, _locale, translated = _validated_packet_content(
        packet_path,
        locales_path=locales_path,
        catalog_dir=catalog_dir,
    )
    review = packet.get("review")
    if not isinstance(review, dict) or review.get("status") != "reviewed":
        raise ValueError("fluent human review status is required")
    translator = review.get("translated_by")
    reviewer = review.get("reviewed_by")
    if not isinstance(translator, str) or not translator.strip():
        raise ValueError("translated_by is required")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError("reviewed_by is required")
    if translator.strip().casefold() == reviewer.strip().casefold():
        raise ValueError("translated_by and reviewed_by must identify different people")
    try:
        date.fromisoformat(review.get("reviewed_at"))
    except (TypeError, ValueError):
        raise ValueError("reviewed_at must be an ISO date") from None

    catalogue = {
        "schema_version": 1,
        "locale": locale,
        "review": {
            "status": "reviewed",
            "translated_by": translator.strip(),
            "reviewed_by": reviewer.strip(),
            "reviewed_at": review["reviewed_at"],
        },
        "messages": translated,
    }
    return catalogue


def render_review_preview(
    packet_path: Path,
    *,
    locales_path: Path = DEFAULT_LOCALES_PATH,
    catalog_dir: Path = DEFAULT_CATALOG_DIR,
) -> str:
    """Render a complete draft packet as a local-only, non-publishable review sheet."""

    packet, locale, locale_entry, translated = _validated_packet_content(
        packet_path,
        locales_path=locales_path,
        catalog_dir=catalog_dir,
    )
    direction = str(locale_entry.get("direction"))
    label = str(locale_entry.get("label") or locale)
    entries = packet["entries"]
    sections = sorted({str(entry["section"]) for entry in entries.values()})
    critical_count = sum(entry["risk"] == "safety_critical" for entry in entries.values())
    section_links = "".join(
        f'<li><a href="#{escape(section, quote=True)}">{escape(section)}</a></li>' for section in sections
    )
    cards: list[str] = []
    for section in sections:
        cards.append(f'<section aria-labelledby="section-{escape(section, quote=True)}">')
        cards.append(f'<h2 id="section-{escape(section, quote=True)}">{escape(section)}</h2>')
        for key in sorted(key for key, entry in entries.items() if entry["section"] == section):
            entry = entries[key]
            risk = str(entry["risk"])
            cards.extend((
                f'<article class="entry {escape(risk, quote=True)}">',
                f'<div class="entry-heading"><h3><code>{escape(key)}</code></h3><span>{escape(risk.replace("_", " "))}</span></div>',
                '<h4>English source</h4>',
                f'<p lang="en" dir="ltr">{escape(str(entry["source"]))}</p>',
                f'<h4>{escape(label)} translation</h4>',
                f'<p class="translation" lang="{escape(locale, quote=True)}" dir="{escape(direction, quote=True)}">{escape(translated[key])}</p>',
                '</article>',
            ))
        cards.append('</section>')
    return f"""<!doctype html>
<html lang="{escape(locale, quote=True)}" dir="{escape(direction, quote=True)}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex, nofollow">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
  <title>{escape(label)} translation review — local draft</title>
  <style>
    :root {{ color-scheme: light; font-family: system-ui, sans-serif; background: #f8fafc; color: #172033; }}
    body {{ margin: 0; }} main {{ max-width: 72rem; margin: auto; padding: 1.5rem; }}
    .warning {{ border: 3px solid #9a3412; background: #fff7ed; padding: 1rem; font-weight: 700; }}
    .summary {{ display: flex; flex-wrap: wrap; gap: 1rem; padding: 0; list-style: none; }}
    nav ul {{ display: flex; flex-wrap: wrap; gap: .75rem; padding: 0; list-style: none; }}
    a {{ color: #075985; }} section {{ margin-block: 2rem; }}
    .entry {{ background: white; border: 1px solid #cbd5e1; border-inline-start: .4rem solid #64748b; border-radius: .4rem; margin-block: 1rem; padding: 1rem; }}
    .entry.safety_critical {{ border-inline-start-color: #b91c1c; }}
    .entry-heading {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: .75rem; }}
    h3, h4 {{ margin-block: .25rem; }} p {{ line-height: 1.55; overflow-wrap: anywhere; }}
    .translation {{ font-size: 1.2rem; }} code {{ direction: ltr; unicode-bidi: isolate; }}
    @media (forced-colors: active) {{ .entry {{ border: 2px solid CanvasText; }} }}
  </style>
</head>
<body>
<main>
  <p class="warning" role="alert">LOCAL DRAFT — NOT REVIEWED, NOT PUBLISHABLE, AND NOT PART OF THE SIR SAATHI RUNTIME.</p>
  <h1>{escape(label)} translation review sheet</h1>
  <p>Compare every translated string with its current English source. Safety-critical entries need extra civic and workflow review. This sheet contains no voter data and makes no approval claim.</p>
  <ul class="summary"><li><strong>{len(translated)}</strong> total entries</li><li><strong>{critical_count}</strong> safety-critical entries</li><li>Direction: <strong>{escape(direction.upper())}</strong></li></ul>
  <nav aria-label="Translation sections"><h2>Sections</h2><ul>{section_links}</ul></nav>
  {''.join(cards)}
</main>
</body>
</html>
"""


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
            translator = review.get("translated_by")
            reviewer = review.get("reviewed_by")
            reviewed_at = review.get("reviewed_at")
            if not isinstance(translator, str) or not translator.strip():
                blockers.append("translated_by is required")
            if not isinstance(reviewer, str) or not reviewer.strip():
                blockers.append("reviewed_by is required")
            if (
                isinstance(translator, str)
                and translator.strip()
                and isinstance(reviewer, str)
                and reviewer.strip()
                and translator.strip().casefold() == reviewer.strip().casefold()
            ):
                blockers.append("translated_by and reviewed_by must identify different people")
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
    seen_codes: set[str] = set()
    for entry in locales:
        if not isinstance(entry, dict) or not isinstance(entry.get("code"), str):
            raise ValueError("each locale registry entry must have a string code")
        code = entry["code"]
        status = entry.get("status")
        if code in seen_codes:
            raise ValueError(f"duplicate locale registry code: {code}")
        seen_codes.add(code)
        if entry.get("direction") not in {"ltr", "rtl"}:
            raise ValueError(f"locale {code} must declare ltr or rtl direction")
        if status not in {"available", "planned"}:
            raise ValueError(f"locale {code} has unsupported registry status")
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


def _safe_review_preview_output(output: Path, catalog_dir: Path) -> Path:
    resolved = output.resolve()
    if resolved.suffix.casefold() != ".html":
        raise ValueError("translation review preview output must end in .html")
    forbidden_roots = (
        catalog_dir.resolve(),
        (ROOT / "apps" / "web" / "public").resolve(),
        (ROOT / "apps" / "web" / "dist").resolve(),
    )
    if any(resolved == root or resolved.is_relative_to(root) for root in forbidden_roots):
        raise ValueError("translation review previews cannot be written to runtime or public web directories")
    if resolved == ROOT or ROOT in resolved.parents:
        ignored_roots = tuple((ROOT / directory).resolve() for directory in ("data", "reports", "samples"))
        if not any(resolved.is_relative_to(root) for root in ignored_roots):
            raise ValueError("repository translation previews must stay under ignored data/, reports/, or samples/ paths")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Report safe UI translation catalogue readiness.")
    parser.add_argument("--locales", type=Path, default=DEFAULT_LOCALES_PATH)
    parser.add_argument("--catalog-dir", type=Path, default=DEFAULT_CATALOG_DIR)
    parser.add_argument("--fail-on-invalid-available", action="store_true")
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument("--create-review-packet", metavar="LOCALE")
    actions.add_argument("--compile-reviewed-packet", type=Path, metavar="PACKET")
    actions.add_argument("--render-review-preview", type=Path, metavar="PACKET")
    parser.add_argument("--output", type=Path, help="Destination for a review packet or compiled catalogue.")
    parser.add_argument("--replace", action="store_true", help="Explicitly replace an existing output file.")
    args = parser.parse_args(argv)

    if args.create_review_packet or args.compile_reviewed_packet or args.render_review_preview:
        if args.output is None:
            parser.error("--output is required for review packet actions")
        try:
            output = args.output.resolve()
            if output.exists() and not args.replace:
                raise ValueError("output already exists; use --replace only after preserving prior review work")
            if args.render_review_preview:
                output = _safe_review_preview_output(output, args.catalog_dir)
                rendered = render_review_preview(
                    args.render_review_preview,
                    locales_path=args.locales,
                    catalog_dir=args.catalog_dir,
                )
                locale = _load_json(args.render_review_preview).get("locale")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered, encoding="utf-8")
                print(json.dumps({
                    "locale": locale,
                    "publishable": False,
                    "review_preview_written": str(args.output),
                }, sort_keys=True))
                return 0
            if args.create_review_packet:
                if output.is_relative_to(args.catalog_dir.resolve()):
                    raise ValueError("draft review packets cannot be written to the runtime catalogue directory")
                repository_config = args.locales.resolve() == DEFAULT_LOCALES_PATH.resolve()
                repository_catalogues = args.catalog_dir.resolve() == DEFAULT_CATALOG_DIR.resolve()
                local_roots = ((ROOT / "data").resolve(), (ROOT / "samples").resolve())
                if repository_config and repository_catalogues and not any(
                    output.is_relative_to(root) for root in local_roots
                ):
                    raise ValueError("repository review packets must stay under ignored data/ or samples/ paths")
                payload = create_review_packet(
                    args.create_review_packet,
                    locales_path=args.locales,
                    catalog_dir=args.catalog_dir,
                )
            else:
                payload = compile_reviewed_packet(
                    args.compile_reviewed_packet,
                    locales_path=args.locales,
                    catalog_dir=args.catalog_dir,
                )
                expected_output = (args.catalog_dir / f"{payload['locale']}.json").resolve()
                if args.output.resolve() != expected_output:
                    raise ValueError(f"reviewed catalogue output must be {expected_output}")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            parser.error(str(exc))
        print(json.dumps({"written": str(args.output), "locale": payload["locale"]}, sort_keys=True))
        return 0

    report = translation_readiness(locales_path=args.locales, catalog_dir=args.catalog_dir)
    print(json.dumps(report, indent=2, sort_keys=True))
    invalid_available = any(
        item["registry_status"] == "available" and not item["publishable"] for item in report["locales"]
    )
    return 1 if args.fail_on_invalid_available and invalid_available else 0


if __name__ == "__main__":
    raise SystemExit(main())
