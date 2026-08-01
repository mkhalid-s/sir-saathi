from pathlib import Path

from pipeline.sir_saathi_pipeline import migrations
from scripts import check_postgres_integration


def test_migration_catalogue_is_ordered_and_has_a_self_contained_baseline() -> None:
    catalogue = migrations.load_migrations()

    assert [migration.migration_id for migration in catalogue] == sorted(
        migration.migration_id for migration in catalogue
    )
    assert len(catalogue) == 8
    assert "CREATE EXTENSION IF NOT EXISTS pg_trgm" in catalogue[0].sql
    assert "\\i" not in catalogue[0].sql
    assert "public_search_scopes" not in catalogue[0].sql
    assert all(len(migration.checksum) == 64 for migration in catalogue)
    assert "public_search_scope_events_enable_dual_control" in catalogue[-1].sql
    assert "UPDATE public_search_scopes\nSET enabled = FALSE" in catalogue[-1].sql


def test_migration_plan_is_dry_run_friendly_and_detects_history_drift() -> None:
    catalogue = migrations.load_migrations()
    clean = {migration.migration_id: migration.checksum for migration in catalogue}

    pending = migrations.migration_plan(catalogue, {})
    assert pending["pending_count"] == 8
    assert pending["ready_to_apply"] is True
    assert migrations.migration_plan(catalogue, clean)["pending_count"] == 0

    drifted = {**clean, catalogue[0].migration_id: "0" * 64}
    assert migrations.migration_plan(catalogue, drifted)["blockers"] == [
        f"checksum drift: {catalogue[0].migration_id}"
    ]
    unknown = {**clean, "9999_missing": "0" * 64}
    assert migrations.migration_plan(catalogue, unknown)["blockers"] == [
        "database migration missing locally: 9999_missing"
    ]


def test_migration_cli_requires_environment_owned_database_url(monkeypatch, capsys) -> None:
    monkeypatch.delenv(migrations.DATABASE_URL_ENV, raising=False)

    assert migrations.main([]) == 2
    output = capsys.readouterr().out
    assert migrations.DATABASE_URL_ENV in output
    assert "postgresql://" not in output


def test_migration_files_never_contain_transaction_control() -> None:
    for path in sorted((Path(__file__).resolve().parents[1] / "db/migrations").glob("*.sql")):
        sql = path.read_text(encoding="utf-8").upper()
        assert "BEGIN;" not in sql
        assert "COMMIT;" not in sql


def test_postgres_integration_check_requires_an_environment_owned_url(monkeypatch, capsys) -> None:
    monkeypatch.delenv(migrations.DATABASE_URL_ENV, raising=False)

    assert check_postgres_integration.main() == 1
    output = capsys.readouterr().out
    assert "integration.database_url_missing" in output
    assert "postgresql://" not in output


def test_ci_applies_real_migrations_to_disposable_postgres_16() -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    integration = (Path(__file__).resolve().parents[1] / "scripts/check_postgres_integration.py").read_text(
        encoding="utf-8"
    )

    assert "image: postgres:16" in workflow
    assert "python scripts/check_postgres_integration.py" in workflow
    assert "voter_record_count" in integration
    assert "integration.dual_control_constraint" in integration
    assert "integration.append_only_event_trigger" in integration
    assert "values_redacted" in integration
