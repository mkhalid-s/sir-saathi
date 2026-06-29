#!/usr/bin/env python3
"""Full local gate before committing or pushing an autonomous slice."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def run(command: list[str]) -> None:
    env = dict(os.environ)
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("ASTRO_TELEMETRY_DISABLED", "1")
    subprocess.check_call(command, cwd=ROOT, env=env)


def last_commit_message() -> str:
    return subprocess.check_output(["git", "-C", str(ROOT), "log", "-1", "--pretty=%B"], text=True)


def main() -> int:
    run([sys.executable, "scripts/check_sensitive.py"])
    run([sys.executable, "-m", "pytest"])
    run(["npm", "audit", "--workspace", "apps/web"])
    run(["npm", "run", "web:build"])
    run([sys.executable, "scripts/launch_gate.py"])
    message = last_commit_message()
    blocked_trailer = "Co-authored-by" + ":"
    if blocked_trailer in message:
        print("Last commit contains a co-author trailer.")
        return 1
    print("Slice gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
