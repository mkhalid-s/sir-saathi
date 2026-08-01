"""Checksum-pinned, serialized PostgreSQL schema migrations for operators."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = ROOT / "db/migrations"
MIGRATION_NAME = re.compile(r"^\d{4}_[a-z0-9_]+\.sql$")
MIGRATION_LOCK_ID = 1_936_876_914
DATABASE_URL_ENV = "SIR_SAATHI_DATABASE_URL"


@dataclass(frozen=True)
class Migration:
    migration_id: str
    checksum: str
    sql: str


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        if not MIGRATION_NAME.fullmatch(path.name):
            raise ValueError(f"invalid migration filename: {path.name}")
        raw = path.read_text(encoding="utf-8")
        if "\\i" in raw:
            raise ValueError(f"psql include is not allowed in {path.name}")
        migrations.append(Migration(path.stem, hashlib.sha256(raw.encode("utf-8")).hexdigest(), raw))
    if not migrations:
        raise ValueError("no database migrations found")
    return migrations


def migration_plan(migrations: list[Migration], applied: dict[str, str]) -> dict[str, Any]:
    local = {migration.migration_id: migration for migration in migrations}
    drift = sorted(
        migration_id
        for migration_id, checksum in applied.items()
        if migration_id in local and local[migration_id].checksum != checksum
    )
    unknown = sorted(set(applied) - set(local))
    pending = [migration.migration_id for migration in migrations if migration.migration_id not in applied]
    blockers = [
        *[f"checksum drift: {migration_id}" for migration_id in drift],
        *[f"database migration missing locally: {migration_id}" for migration_id in unknown],
    ]
    return {
        "applied_count": len(applied),
        "pending": pending,
        "pending_count": len(pending),
        "blockers": blockers,
        "ready_to_apply": not blockers,
    }


def run_migrations(database_url: str, *, apply: bool) -> dict[str, Any]:
    import psycopg

    migrations = load_migrations()
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_id TEXT PRIMARY KEY,
                checksum TEXT NOT NULL CHECK (char_length(checksum) = 64),
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        connection.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK_ID,))
        try:
            rows = connection.execute(
                "SELECT migration_id, checksum FROM schema_migrations ORDER BY migration_id"
            ).fetchall()
            applied = {str(row[0]): str(row[1]) for row in rows}
            report = migration_plan(migrations, applied)
            report["applied"] = []
            report["mode"] = "apply" if apply else "dry_run"
            if report["blockers"]:
                return report
            if apply:
                by_id = {migration.migration_id: migration for migration in migrations}
                for migration_id in report["pending"]:
                    migration = by_id[migration_id]
                    with connection.transaction():
                        connection.execute(migration.sql)
                        connection.execute(
                            "INSERT INTO schema_migrations (migration_id, checksum) VALUES (%s, %s)",
                            (migration.migration_id, migration.checksum),
                        )
                    report["applied"].append(migration_id)
                report["pending"] = []
                report["pending_count"] = 0
            return report
        finally:
            connection.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK_ID,))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan or apply checksum-pinned database migrations.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply pending migrations transactionally.")
    mode.add_argument("--check", action="store_true", help="Fail if migrations are pending.")
    args = parser.parse_args(argv)
    database_url = os.environ.get(DATABASE_URL_ENV)
    if not database_url:
        print(json.dumps({"error": f"{DATABASE_URL_ENV} is required", "ready": False}))
        return 2
    try:
        report = run_migrations(database_url, apply=args.apply)
    except Exception:
        print(json.dumps({"error": "database migration operation failed", "ready": False}))
        return 1
    report["ready"] = not report["blockers"] and (not args.check or report["pending_count"] == 0)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
