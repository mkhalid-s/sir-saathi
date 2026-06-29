#!/usr/bin/env python3
"""Block commits that expose secrets, local paths, or bulk voter data."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = "scripts/check_sensitive.py"

BLOCKED_PATH_PATTERNS = [
    re.compile(r"^data/(?!README\.md$).+"),
    re.compile(r"^samples/.+\.(?:pdf|png|jpe?g|html)$", re.IGNORECASE),
    re.compile(r"^samples/(?:validation|regions)/"),
    re.compile(r"(?:^|/)__pycache__/"),
    re.compile(r"(?:^|/)\.mypy_cache/"),
    re.compile(r"(?:^|/)node_modules/"),
    re.compile(r"(?:^|/)dist/"),
    re.compile(r"(?:^|/)build/"),
    re.compile(r"\.env(?:\..*)?$"),
    re.compile(r"\.(?:pem|key|p12|pfx|crt)$", re.IGNORECASE),
]

CONTENT_PATTERNS = [
    ("coauthor trailer", re.compile(r"Co-authored-by:", re.IGNORECASE)),
    ("company reference", re.compile(r"Guidewire|@guidewire|/workspaces/GW|\bGW\b", re.IGNORECASE)),
    ("local user path", re.compile(r"/Users/[^\s)]+")),
    ("private key", re.compile(r"BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY")),
    ("aws access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github token", re.compile(r"ghp_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]+")),
    ("slack token", re.compile(r"xox[baprs]-[A-Za-z0-9-]+")),
    ("openai-style token", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("full EPIC id", re.compile(r"\b[A-Z]{3}\d{7}\b|MT/\d{2}/\d{3}/\d{7}")),
    ("inline secret assignment", re.compile(r"(?:api[_-]?key|client[_-]?secret|password|credential|token)\s*[:=]", re.IGNORECASE)),
]

TEXT_SUFFIXES = {
    ".astro", ".css", ".csv", ".html", ".js", ".json", ".md", ".mjs",
    ".py", ".sql", ".toml", ".ts", ".tsx", ".txt", ".yml", ".yaml",
}


def git_output(args: list[str]) -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True)


def candidate_files(staged: bool) -> list[str]:
    if staged:
        raw = git_output(["diff", "--cached", "--name-only", "-z"])
        return [p for p in raw.split("\0") if p]
    tracked = git_output(["ls-files", "-z"]).split("\0")
    untracked = git_output(["ls-files", "--others", "--exclude-standard", "-z"]).split("\0")
    return sorted({p for p in tracked + untracked if p})


def staged_content(path: str) -> bytes | None:
    try:
        return subprocess.check_output(["git", "-C", str(ROOT), "show", f":{path}"], stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return None


def working_content(path: str) -> bytes | None:
    file_path = ROOT / path
    if not file_path.is_file():
        return None
    return file_path.read_bytes()


def is_text_candidate(path: str) -> bool:
    return Path(path).suffix.lower() in TEXT_SUFFIXES or Path(path).name in {"Makefile", "Dockerfile"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", action="store_true", help="scan staged files only")
    args = parser.parse_args()

    findings: list[str] = []
    for rel_path in candidate_files(args.staged):
        for pattern in BLOCKED_PATH_PATTERNS:
            if pattern.search(rel_path):
                findings.append(f"blocked path: {rel_path}")
                break

        data = staged_content(rel_path) if args.staged else working_content(rel_path)
        if data is None:
            continue
        if not is_text_candidate(rel_path):
            if b"\0" in data[:4096]:
                findings.append(f"binary candidate: {rel_path}")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(f"non-utf8 text candidate: {rel_path}")
            continue
        if rel_path == SELF:
            # The scanner source necessarily contains the signatures it detects.
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for label, pattern in CONTENT_PATTERNS:
                if pattern.search(line):
                    findings.append(f"{rel_path}:{line_no}: {label}: {line[:160]}")

    if findings:
        print("Sensitive-data scan failed:")
        for finding in findings:
            print(f"- {finding}")
        return 1
    print("Sensitive-data scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
