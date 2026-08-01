from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.deployment_preflight import preflight


def test_guidance_preflight_requires_one_real_https_origin() -> None:
    ready = preflight(
        "guidance",
        {"PUBLIC_SITE_URL": "https://sirsaathi.org", "WEB_URL": "https://sirsaathi.org/"},
    )
    assert ready["ready"] is True
    assert ready["values_redacted"] is True

    invalid = preflight(
        "guidance",
        {"PUBLIC_SITE_URL": "https://sir-saathi.example", "WEB_URL": "http://localhost:4321"},
    )
    assert invalid["ready"] is False
    assert len(invalid["blockers"]) == 2

    malformed = preflight(
        "guidance",
        {"PUBLIC_SITE_URL": "https://sirsaathi.org:invalid", "WEB_URL": "https://[invalid"},
    )
    assert malformed["ready"] is False
    assert len(malformed["blockers"]) == 2

    with pytest.raises(ValueError, match="mode"):
        preflight("unknown", {})

    mismatched = preflight(
        "guidance",
        {
            "PUBLIC_SITE_URL": "https://sirsaathi.org",
            "WEB_URL": "https://sirsaathi.org",
            "SIR_SAATHI_DEPLOYMENT_MODE": "indexed-search",
        },
    )
    assert mismatched["blockers"] == [
        "SIR_SAATHI_DEPLOYMENT_MODE must match the selected deployment mode"
    ]


def test_indexed_search_preflight_checks_secrets_dependencies_and_backup_boundary(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir(mode=0o700)
    environment = {
        "PUBLIC_SITE_URL": "https://sirsaathi.org",
        "WEB_URL": "https://sirsaathi.org/",
        "SIR_SAATHI_DEPLOYMENT_MODE": "indexed-search",
        "PUBLIC_TURNSTILE_SITE_KEY": "public-site-value",
        "SIR_SAATHI_DATABASE_URL": "postgresql://database.internal/sir_saathi",
        "SIR_SAATHI_REDIS_URL": "rediss://redis.internal/0",
        "SIR_SAATHI_TURNSTILE_SECRET": "server-owned-value",
        "SIR_SAATHI_TURNSTILE_HOSTNAME": "sirsaathi.org",
        "SIR_SAATHI_TRUSTED_PROXY_HOPS": "1",
        "SIR_SAATHI_BACKUP_DIR": str(backup_dir),
        "SIR_SAATHI_AGE_RECIPIENT": "age1syntheticrecipient",
    }
    report = preflight("indexed-search", environment)
    assert report == {
        "mode": "indexed-search",
        "ready": True,
        "blockers": [],
        "checked_fields": 11,
        "values_redacted": True,
    }

    environment["SIR_SAATHI_TURNSTILE_HOSTNAME"] = "wrong.example.org"
    environment["SIR_SAATHI_TRUSTED_PROXY_HOPS"] = "0"
    environment["SIR_SAATHI_TURNSTILE_SECRET"] = environment["PUBLIC_TURNSTILE_SITE_KEY"]
    blocked = preflight("indexed-search", environment)
    assert blocked["ready"] is False
    assert len(blocked["blockers"]) == 3


def test_preflight_report_never_contains_configuration_values(tmp_path: Path) -> None:
    private_value = "private-production-value"
    report = preflight(
        "indexed-search",
        {
            "PUBLIC_SITE_URL": "https://sirsaathi.org",
            "WEB_URL": "https://different.example.org",
            "SIR_SAATHI_TURNSTILE_SECRET": private_value,
            "SIR_SAATHI_BACKUP_DIR": str(tmp_path / "missing"),
        },
    )
    assert private_value not in str(report)
    assert "different.example.org" not in str(report)
