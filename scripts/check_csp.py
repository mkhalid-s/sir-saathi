#!/usr/bin/env python3
"""Audit the generated PWA's layered, hash-only inner CSP."""

from __future__ import annotations

import argparse
import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "apps" / "web" / "dist"
TURNSTILE_ORIGIN = "https://challenges.cloudflare.com"
META_MARKER = 'http-equiv="content-security-policy"'
INLINE_SCRIPT = re.compile(r"<script\b(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</script>", re.IGNORECASE)
INLINE_STYLE = re.compile(r"<style\b[^>]*>(?P<body>[\s\S]*?)</style>", re.IGNORECASE)
PROTECTED_ELEMENT = re.compile(r"<(?:script|style)\b|<link\b[^>]*\brel=[\"'][^\"']*stylesheet", re.IGNORECASE)


class SecurityMarkupParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.policies: list[str] = []
        self.inline_attributes: list[str] = []
        self.script_sources: list[str] = []
        self.stylesheet_sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {name.casefold(): value or "" for name, value in attrs}
        if tag == "meta" and values.get("http-equiv", "").casefold() == "content-security-policy":
            self.policies.append(values.get("content", ""))
        for name in values:
            if name == "style" or name.startswith("on"):
                self.inline_attributes.append(name)
        if tag == "script" and "src" in values:
            self.script_sources.append(values["src"])
        if tag == "link" and "stylesheet" in values.get("rel", "").casefold().split():
            self.stylesheet_sources.append(values.get("href", ""))


def _directives(policy: str) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for segment in policy.split(";"):
        tokens = segment.strip().split()
        if tokens:
            parsed[tokens[0].casefold()] = tokens[1:]
    return parsed


def _sha256_source(content: str) -> str:
    digest = base64.b64encode(hashlib.sha256(content.encode("utf-8")).digest()).decode("ascii")
    return f"'sha256-{digest}'"


def _is_same_origin_path(value: str) -> bool:
    return value.startswith("/") and not value.startswith("//")


def audit_html(html: str, *, page: str = "page") -> tuple[list[str], set[str], set[str]]:
    issues: list[str] = []
    parser = SecurityMarkupParser()
    parser.feed(html)
    if len(parser.policies) != 1:
        issues.append(f"{page}: expected exactly one CSP meta policy")
        return issues, set(), set()

    policy = parser.policies[0]
    directives = _directives(policy)
    required = {
        "default-src": {"'none'"},
        "base-uri": {"'none'"},
        "object-src": {"'none'"},
        "form-action": {"'self'"},
        "img-src": {"'self'", "data:"},
        "font-src": {"'self'"},
        "connect-src": {"'self'", TURNSTILE_ORIGIN},
        "frame-src": {TURNSTILE_ORIGIN},
        "worker-src": {"'self'"},
        "manifest-src": {"'self'"},
    }
    for directive, expected in required.items():
        if not expected.issubset(set(directives.get(directive, []))):
            issues.append(f"{page}: CSP {directive} is missing required sources")

    script_sources = set(directives.get("script-src", []))
    style_sources = set(directives.get("style-src", []))
    if "'self'" not in script_sources or TURNSTILE_ORIGIN not in script_sources:
        issues.append(f"{page}: script-src is not same-origin and Turnstile compatible")
    if "'self'" not in style_sources:
        issues.append(f"{page}: style-src must allow same-origin stylesheets")
    forbidden = {"'unsafe-inline'", "'unsafe-eval'", "data:", "blob:"}
    if forbidden & script_sources:
        issues.append(f"{page}: script-src contains an unsafe source")
    if forbidden & style_sources:
        issues.append(f"{page}: style-src contains an unsafe source")
    if any(source.startswith("'nonce-") for source in script_sources | style_sources):
        issues.append(f"{page}: static CSP must use build hashes, not reusable nonces")

    meta_position = html.casefold().find(META_MARKER)
    first_protected = PROTECTED_ELEMENT.search(html)
    if meta_position < 0 or (first_protected and meta_position > first_protected.start()):
        issues.append(f"{page}: CSP meta must precede every protected resource")
    if parser.inline_attributes:
        issues.append(f"{page}: inline style or event-handler attributes are not allowed")
    for source in parser.script_sources:
        if not (_is_same_origin_path(source) or source.startswith(f"{TURNSTILE_ORIGIN}/")):
            issues.append(f"{page}: script element uses an unapproved origin")
    for source in parser.stylesheet_sources:
        if not _is_same_origin_path(source):
            issues.append(f"{page}: stylesheet uses an unapproved origin")

    inline_script_hashes: set[str] = set()
    for match in INLINE_SCRIPT.finditer(html):
        if re.search(r"\bsrc\s*=", match.group("attrs"), re.IGNORECASE):
            continue
        source = _sha256_source(match.group("body"))
        inline_script_hashes.add(source)
        if source not in script_sources:
            issues.append(f"{page}: inline script hash is absent from script-src")
    inline_style_hashes = {_sha256_source(match.group("body")) for match in INLINE_STYLE.finditer(html)}
    for source in inline_style_hashes:
        if source not in style_sources:
            issues.append(f"{page}: inline style hash is absent from style-src")
    if not any(source.startswith("'sha256-") for source in script_sources):
        issues.append(f"{page}: script-src has no build-generated SHA-256 hashes")
    if not any(source.startswith("'sha256-") for source in style_sources):
        issues.append(f"{page}: style-src has no build-generated SHA-256 hashes")
    return issues, inline_script_hashes, inline_style_hashes


def audit_directory(dist: Path) -> dict[str, object]:
    pages = sorted(dist.rglob("*.html"))
    if not pages:
        raise ValueError(f"no generated HTML pages found under {dist}")
    issues: list[str] = []
    script_hashes: set[str] = set()
    style_hashes: set[str] = set()
    for path in pages:
        page_issues, page_scripts, page_styles = audit_html(
            path.read_text(encoding="utf-8"), page=str(path.relative_to(dist))
        )
        issues.extend(page_issues)
        script_hashes.update(page_scripts)
        style_hashes.update(page_styles)
    return {
        "page_count": len(pages),
        "inline_script_hash_count": len(script_hashes),
        "inline_style_hash_count": len(style_hashes),
        "issue_count": len(issues),
        "issues": issues,
        "passed": not issues,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit generated PWA CSP hashes and sources.")
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    args = parser.parse_args(argv)
    try:
        report = audit_directory(args.dist)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
