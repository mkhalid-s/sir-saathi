#!/usr/bin/env python3
"""Launch readiness checks for public SIR Saathi slices."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "apps/web/src/pages/privacy.astro",
    "apps/web/src/pages/methodology.astro",
    "apps/web/src/pages/data-use.astro",
    "docs/PRIVACY_AND_ABUSE.md",
    "docs/LAUNCH_CHECKLIST.md",
    "services/api/privacy.py",
]


def run(command: list[str]) -> None:
    env = dict(os.environ)
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    subprocess.check_call(command, cwd=ROOT, env=env)


def main() -> int:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    if missing:
        print("Missing launch files:")
        for path in missing:
            print(f"- {path}")
        return 1
    run([sys.executable, "scripts/check_sensitive.py"])
    run([sys.executable, "-m", "pytest"])
    print("Launch gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
