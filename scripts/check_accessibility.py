#!/usr/bin/env python3
"""Audit structural accessibility invariants in the generated static PWA.

This is a deterministic baseline, not a claim of complete WCAG conformance.
Manual assistive-technology and zoom testing remains part of release review.
"""

from __future__ import annotations

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = ROOT / "apps" / "web" / "dist"
VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.ids: Counter[str] = Counter()
        self.references: list[tuple[str, str]] = []
        self.controls: list[tuple[str, str | None, bool]] = []
        self.labels_for: set[str] = set()
        self.html_lang: str | None = None
        self.html_dir: str | None = None
        self.main_count = 0
        self.h1_count = 0
        self.skip_target: str | None = None
        self.title_parts: list[str] = []
        self.in_title = False
        self.blank_link_issues = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        element_id = values.get("id")
        if element_id:
            self.ids[element_id] += 1
        for attribute in ("aria-labelledby", "aria-describedby"):
            for reference in values.get(attribute, "").split():
                self.references.append((attribute, reference))
        if tag == "html":
            self.html_lang = values.get("lang")
            self.html_dir = values.get("dir")
        elif tag == "main":
            self.main_count += 1
        elif tag == "h1":
            self.h1_count += 1
        elif tag == "title":
            self.in_title = True
        elif tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        elif tag in {"input", "select", "textarea"} and values.get("type") != "hidden":
            directly_named = bool(values.get("aria-label") or values.get("aria-labelledby") or "label" in self.stack)
            self.controls.append((tag, element_id, directly_named))
        elif tag == "a":
            classes = values.get("class", "").split()
            if "skip-link" in classes:
                self.skip_target = values.get("href")
            if values.get("target") == "_blank" and "noreferrer" not in values.get("rel", "").split():
                self.blank_link_issues += 1
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag in self.stack:
            reverse_index = self.stack[::-1].index(tag)
            del self.stack[len(self.stack) - reverse_index - 1 :]

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)


def audit_html(html: str, *, page: str = "page") -> list[str]:
    parser = PageParser()
    parser.feed(html)
    issues: list[str] = []
    if not parser.html_lang:
        issues.append(f"{page}: html lang is missing")
    if parser.html_dir not in {"ltr", "rtl"}:
        issues.append(f"{page}: html dir must be ltr or rtl")
    if not "".join(parser.title_parts).strip():
        issues.append(f"{page}: title is empty")
    if parser.main_count != 1:
        issues.append(f"{page}: expected exactly one main landmark")
    if parser.h1_count != 1:
        issues.append(f"{page}: expected exactly one h1")
    if parser.skip_target != "#main-content" or "main-content" not in parser.ids:
        issues.append(f"{page}: skip link must target main-content")
    for element_id, count in parser.ids.items():
        if count > 1:
            issues.append(f"{page}: duplicate id {element_id}")
    for attribute, reference in parser.references:
        if reference not in parser.ids:
            issues.append(f"{page}: {attribute} references missing id {reference}")
    for tag, element_id, directly_named in parser.controls:
        if not directly_named and (not element_id or element_id not in parser.labels_for):
            issues.append(f"{page}: {tag} control has no accessible label")
    if parser.blank_link_issues:
        issues.append(f"{page}: {parser.blank_link_issues} new-tab link(s) omit noreferrer")
    return issues


def audit_directory(dist: Path) -> dict[str, object]:
    pages = sorted(dist.rglob("*.html"))
    if not pages:
        raise ValueError(f"no generated HTML pages found under {dist}")
    issues = [
        issue
        for path in pages
        for issue in audit_html(path.read_text(encoding="utf-8"), page=str(path.relative_to(dist)))
    ]
    return {"page_count": len(pages), "issue_count": len(issues), "issues": issues, "passed": not issues}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit generated PWA accessibility structure.")
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
