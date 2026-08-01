#!/usr/bin/env python3
"""Audit shared CSS colour roles and critical focus/control declarations."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STYLESHEET = ROOT / "apps" / "web" / "src" / "styles" / "global.css"
TOKEN_PATTERN = re.compile(r"(--color-[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})\s*;")
AUDITED_PAIRS = (
    ("text.body", "--color-ink", "--color-canvas", 4.5),
    ("text.field", "--color-field", "--color-surface", 4.5),
    ("text.muted_surface", "--color-muted", "--color-surface", 4.5),
    ("text.muted_canvas", "--color-muted", "--color-canvas", 4.5),
    ("text.subtle_canvas", "--color-subtle", "--color-canvas", 4.5),
    ("text.link_surface", "--color-link", "--color-surface", 4.5),
    ("text.link_canvas", "--color-link", "--color-canvas", 4.5),
    ("text.hero_eyebrow", "--color-hero-eyebrow", "--color-ink", 4.5),
    ("text.hero_copy", "--color-hero-copy", "--color-ink", 4.5),
    ("text.offline", "--color-offline-text", "--color-offline-surface", 4.5),
    ("text.warning", "--color-warning-text", "--color-surface", 4.5),
    ("text.notice", "--color-muted", "--color-notice-surface", 4.5),
    ("text.primary_button", "--color-surface", "--color-ink", 4.5),
    ("non_text.focus_light", "--color-focus", "--color-surface", 3.0),
    ("non_text.focus_dark", "--color-focus", "--color-ink", 3.0),
    ("non_text.control_boundary", "--color-control-border", "--color-surface", 3.0),
    ("non_text.dark_control_boundary", "--color-dark-control-border", "--color-ink", 3.0),
)
REQUIRED_DECLARATIONS = {
    ":focus-visible": ("outline: 3px solid var(--color-focus)", "outline-offset: 3px"),
    ".connectivity-notice": (
        "background: var(--color-offline-surface)",
        "color: var(--color-offline-text)",
    ),
    ".locale-switcher a": ("border: 1px solid var(--color-control-border)",),
    ".hero": ("background: var(--color-ink)", "color: var(--color-surface)"),
    ".input,\n.select": (
        "border: 1px solid var(--color-control-border)",
        "background: var(--color-surface)",
        "color: var(--color-ink)",
    ),
    ".primary-button": ("background: var(--color-ink)", "color: var(--color-surface)"),
    ".secondary-button": ("border: 1px solid var(--color-control-border)",),
    ".secondary-button.light": ("border-color: var(--color-dark-control-border)",),
    ".warning-note": ("color: var(--color-warning-text)",),
}


def _rgb(value: str) -> tuple[float, float, float]:
    raw = value.lstrip("#")
    if len(raw) == 3:
        raw = "".join(character * 2 for character in raw)
    return tuple(int(raw[index:index + 2], 16) / 255 for index in (0, 2, 4))  # type: ignore[return-value]


def _luminance(value: str) -> float:
    channels = tuple(
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in _rgb(value)
    )
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _selector_block(css: str, selector: str) -> str | None:
    matches = re.findall(rf"(?:^|\n){re.escape(selector)}\s*\{{([^{{}}]*)\}}", css)
    return matches[-1] if matches else None


def audit_stylesheet(css: str) -> dict[str, object]:
    tokens = dict(TOKEN_PATTERN.findall(css))
    blockers: list[str] = []
    ratios: dict[str, float] = {}
    for identifier, foreground, background, minimum in AUDITED_PAIRS:
        if foreground not in tokens or background not in tokens:
            blockers.append(f"token.{identifier}.missing")
            continue
        ratio = contrast_ratio(tokens[foreground], tokens[background])
        ratios[identifier] = round(ratio, 2)
        if ratio + 1e-9 < minimum:
            blockers.append(f"contrast.{identifier}.below_{minimum:g}")
    for selector, declarations in REQUIRED_DECLARATIONS.items():
        block = _selector_block(css, selector)
        if block is None:
            blockers.append(f"selector.{selector}.missing")
            continue
        normalized = " ".join(block.split())
        for declaration in declarations:
            if declaration not in normalized:
                blockers.append(f"selector.{selector}.missing_declaration")
                break
    return {
        "audited_pair_count": len(AUDITED_PAIRS),
        "blockers": blockers,
        "passed": not blockers,
        "ratios": ratios,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit shared CSS contrast and focus/control roles.")
    parser.add_argument("--stylesheet", type=Path, default=DEFAULT_STYLESHEET)
    args = parser.parse_args(argv)
    try:
        report = audit_stylesheet(args.stylesheet.read_text(encoding="utf-8"))
    except OSError:
        report = {"audited_pair_count": 0, "blockers": ["stylesheet.unreadable"], "passed": False, "ratios": {}}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
