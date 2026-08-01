from pathlib import Path

import pytest

from pipeline.sir_saathi_pipeline.deployment_preflight import preflight

RELEASE_COMMIT = "b" * 40


def release_environment() -> dict[str, str]:
    return {
        "PUBLIC_RELEASE_COMMIT": RELEASE_COMMIT,
        "SIR_SAATHI_RELEASE_COMMIT": RELEASE_COMMIT,
    }


def test_guidance_preflight_requires_one_real_https_origin() -> None:
    ready = preflight(
        "guidance",
        {"PUBLIC_SITE_URL": "https://sirsaathi.org", "WEB_URL": "https://sirsaathi.org/", **release_environment()},
    )
    assert ready["ready"] is True
    assert ready["checked_fields"] == 5
    assert ready["values_redacted"] is True

    invalid = preflight(
        "guidance",
        {"PUBLIC_SITE_URL": "https://sir-saathi.example", "WEB_URL": "http://localhost:4321", **release_environment()},
    )
    assert invalid["ready"] is False
    assert len(invalid["blockers"]) == 2

    malformed = preflight(
        "guidance",
        {"PUBLIC_SITE_URL": "https://sirsaathi.org:invalid", "WEB_URL": "https://[invalid", **release_environment()},
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
            **release_environment(),
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
        **release_environment(),
    }
    report = preflight("indexed-search", environment)
    assert report == {
        "mode": "indexed-search",
        "ready": True,
        "blockers": [],
        "checked_fields": 13,
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
            **release_environment(),
        },
    )
    assert private_value not in str(report)
    assert "different.example.org" not in str(report)


def test_preflight_rejects_missing_malformed_or_mixed_release_commits() -> None:
    base = {"PUBLIC_SITE_URL": "https://sirsaathi.org", "WEB_URL": "https://sirsaathi.org"}
    missing = preflight("guidance", base)
    assert missing["blockers"] == [
        "PUBLIC_RELEASE_COMMIT must be the full lowercase Git commit",
        "SIR_SAATHI_RELEASE_COMMIT must be the full lowercase Git commit",
    ]
    mixed = preflight("guidance", {
        **base,
        "PUBLIC_RELEASE_COMMIT": "a" * 40,
        "SIR_SAATHI_RELEASE_COMMIT": "b" * 40,
    })
    assert mixed["blockers"] == ["PWA and API release commits must match"]
