#!/usr/bin/env python3
"""Validate canonical, alternate, sitemap, and robots metadata in the built PWA."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "apps/web/dist"


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.lang = ""
        self.canonicals: list[str] = []
        self.alternates: dict[str, str] = {}
        self.noindex = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "html":
            self.lang = attributes.get("lang") or ""
        if tag != "link":
            if tag == "meta" and attributes.get("name", "").casefold() == "robots":
                directives = attributes.get("content", "").casefold().replace(",", " ").split()
                self.noindex = "noindex" in directives
            return
        relations = set((attributes.get("rel") or "").split())
        href = attributes.get("href") or ""
        if "canonical" in relations:
            self.canonicals.append(href)
        if "alternate" in relations and attributes.get("hreflang"):
            self.alternates[attributes["hreflang"] or ""] = href


def page_path(html_path: Path) -> str:
    relative = html_path.relative_to(DIST).as_posix()
    if relative == "index.html":
        return "/"
    if relative.endswith("/index.html"):
        return f"/{relative[:-len('index.html')]}"
    return f"/{relative}"


def main(argv: list[str] | None = None) -> int:
    argument_parser = argparse.ArgumentParser(description="Audit generated public URL metadata.")
    argument_parser.add_argument(
        "--require-production-origin",
        action="store_true",
        help="Reject reserved .example origins in release output.",
    )
    args = argument_parser.parse_args(argv)
    issues: list[str] = []
    canonical_urls: set[str] = set()
    expected_languages: set[str] | None = None
    origins: set[str] = set()
    noindex_pages: list[str] = []
    html_paths = sorted(DIST.rglob("*.html"))
    if not html_paths:
        issues.append("no generated HTML pages found")

    for html_path in html_paths:
        parser = MetadataParser()
        parser.feed(html_path.read_text(encoding="utf-8"))
        label = html_path.relative_to(DIST).as_posix()
        if parser.noindex:
            noindex_pages.append(label)
            if parser.canonicals or parser.alternates:
                issues.append(f"{label}: noindex page must not publish canonical or locale alternates")
            continue
        if len(parser.canonicals) != 1:
            issues.append(f"{label}: expected exactly one canonical URL")
            continue
        canonical = parser.canonicals[0]
        parsed = urlparse(canonical)
        if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
            issues.append(f"{label}: canonical URL must be absolute HTTPS without query or fragment")
        if parsed.path != page_path(html_path):
            issues.append(f"{label}: canonical path {parsed.path!r} does not match generated page")
        if canonical in canonical_urls:
            issues.append(f"{label}: duplicate canonical URL {canonical}")
        canonical_urls.add(canonical)
        origins.add(f"{parsed.scheme}://{parsed.netloc}")

        alternate_languages = set(parser.alternates)
        if parser.lang not in alternate_languages:
            issues.append(f"{label}: missing self-language alternate for {parser.lang!r}")
        if "en" not in alternate_languages or "x-default" not in alternate_languages:
            issues.append(f"{label}: alternates must include English and x-default")
        if expected_languages is None:
            expected_languages = alternate_languages
        elif alternate_languages != expected_languages:
            issues.append(f"{label}: locale alternate set differs from other pages")
        for language, href in parser.alternates.items():
            alternate = urlparse(href)
            if alternate.scheme != "https" or not alternate.netloc:
                issues.append(f"{label}: {language} alternate is not absolute HTTPS")
            if f"{alternate.scheme}://{alternate.netloc}" not in origins and origins:
                issues.append(f"{label}: {language} alternate uses a different origin")

    sitemap_path = DIST / "sitemap.xml"
    if not sitemap_path.is_file():
        issues.append("sitemap.xml was not generated")
        sitemap_urls: set[str] = set()
    else:
        root = ET.parse(sitemap_path).getroot()
        sitemap_urls = {
            element.text or ""
            for element in root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
        }
        if sitemap_urls != canonical_urls:
            issues.append("sitemap URLs do not exactly match generated canonical pages")

    robots_path = DIST / "robots.txt"
    robots = robots_path.read_text(encoding="utf-8") if robots_path.is_file() else ""
    if "User-agent: *\nAllow: /\n" not in robots:
        issues.append("robots.txt must explicitly allow public guidance pages")
    if len(origins) != 1:
        issues.append("generated pages must use exactly one canonical origin")
    else:
        origin = next(iter(origins))
        if f"Sitemap: {origin}/sitemap.xml" not in robots:
            issues.append("robots.txt must point to the canonical sitemap")
        if args.require_production_origin and urlparse(origin).hostname and urlparse(origin).hostname.endswith(".example"):
            issues.append("production output must not use a reserved .example origin")
    if noindex_pages != ["404.html"]:
        issues.append("generated site must contain exactly one noindex document at 404.html")

    report = {
        "alternate_languages": sorted(expected_languages or []),
        "issue_count": len(issues),
        "issues": issues,
        "page_count": len(html_paths),
        "noindex_pages": noindex_pages,
        "passed": not issues,
        "sitemap_url_count": len(sitemap_urls),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
