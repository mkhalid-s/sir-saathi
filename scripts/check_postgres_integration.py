#!/usr/bin/env python3
"""Apply and exercise migrations in an empty, disposable PostgreSQL 16 database."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.sir_saathi_pipeline.migrations import DATABASE_URL_ENV, load_migrations, run_migrations

EXPECTED_TABLES = {
    "assembly_constituencies",
    "public_search_scope_events",
    "public_search_scopes",
    "roll_versions",
    "schema_migrations",
    "states",
    "voter_records",
}


def _fail(blocker: str) -> int:
    print(json.dumps({"passed": False, "blockers": [blocker], "values_redacted": True}, sort_keys=True))
    return 1


def check_database(database_url: str) -> dict[str, object]:
    import psycopg
    from psycopg.errors import CheckViolation, RaiseException

    migrations = load_migrations()
    dry_run = run_migrations(database_url, apply=False)
    if dry_run["blockers"] or dry_run["pending_count"] != len(migrations):
        raise RuntimeError("integration.initial_migration_plan")
    applied = run_migrations(database_url, apply=True)
    if applied["blockers"] or applied["pending_count"] or applied["applied"] != [item.migration_id for item in migrations]:
        raise RuntimeError("integration.migration_apply")
    checked = run_migrations(database_url, apply=False)
    if checked["blockers"] or checked["pending_count"] or checked["applied_count"] != len(migrations):
        raise RuntimeError("integration.migration_check")

    with psycopg.connect(database_url, autocommit=True) as connection:
        extension = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm')"
        ).fetchone()
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ).fetchall()
        }
        if extension != (True,) or not EXPECTED_TABLES.issubset(tables):
            raise RuntimeError("integration.schema_shape")

        connection.execute(
            """INSERT INTO states
               (state_id, eci_state_code, name, default_language, data_capability, public_launch_ready)
               VALUES ('IN-TEST', 'T99', 'Synthetic test jurisdiction', 'en', 'guidance_only', FALSE)"""
        )
        connection.execute(
            """INSERT INTO assembly_constituencies
               (ac_id, state_id, ac_number, name, geography_version)
               VALUES ('IN-TEST-AC-1', 'IN-TEST', 1, 'Synthetic test AC', 'ci-fixture-v1')"""
        )
        connection.execute(
            """INSERT INTO roll_versions
               (roll_version_id, state_id, roll_year, roll_kind, source_label)
               VALUES ('IN-TEST-ROLL-1', 'IN-TEST', 2000, 'synthetic', 'CI fixture only')"""
        )
        try:
            connection.execute(
                """INSERT INTO public_search_scopes
                   (roll_version_id, ac_id, enabled, operated_by, reviewed_by, reviewed_at)
                   VALUES ('IN-TEST-ROLL-1', 'IN-TEST-AC-1', TRUE, 'same-person', ' same-person ', now())"""
            )
        except CheckViolation:
            pass
        else:
            raise RuntimeError("integration.dual_control_constraint")
        connection.execute(
            """INSERT INTO public_search_scopes
               (roll_version_id, ac_id, enabled, operated_by, reviewed_by, reviewed_at)
               VALUES ('IN-TEST-ROLL-1', 'IN-TEST-AC-1', TRUE, 'ci-operator', 'ci-reviewer', now())"""
        )
        connection.execute(
            """INSERT INTO public_search_scope_events
               (event_id, roll_version_id, ac_id, action, operated_by, reviewed_by, reason, readiness_snapshot)
               VALUES (
                 'IN-TEST-EVENT-1', 'IN-TEST-ROLL-1', 'IN-TEST-AC-1', 'enable',
                 'ci-operator', 'ci-reviewer', 'Synthetic migration integration fixture',
                 '{"safe_aggregate_report":true,"synthetic_fixture":true}'::jsonb
               )"""
        )
        try:
            connection.execute(
                "UPDATE public_search_scope_events SET reason = 'mutation must fail' WHERE event_id = 'IN-TEST-EVENT-1'"
            )
        except RaiseException:
            pass
        else:
            raise RuntimeError("integration.append_only_event_trigger")
        enabled = connection.execute(
            "SELECT count(*) FROM public_search_scopes WHERE enabled"
        ).fetchone()
        voters = connection.execute("SELECT count(*) FROM voter_records").fetchone()
        if enabled != (1,) or voters != (0,):
            raise RuntimeError("integration.synthetic_scope_boundary")

    return {
        "passed": True,
        "migration_count": len(migrations),
        "required_table_count": len(EXPECTED_TABLES),
        "synthetic_scope_exercised": True,
        "voter_record_count": 0,
        "values_redacted": True,
    }


def main() -> int:
    database_url = os.environ.get(DATABASE_URL_ENV, "")
    if not database_url:
        return _fail("integration.database_url_missing")
    try:
        report = check_database(database_url)
    except RuntimeError as error:
        return _fail(str(error))
    except Exception:
        return _fail("integration.database_operation_failed")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
