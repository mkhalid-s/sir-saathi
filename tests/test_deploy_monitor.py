from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_deployment_reference_files_exist() -> None:
    for rel in [
        "docs/DEPLOYMENT_AND_MONITORING.md",
        "docs/RUNBOOK.md",
        "infra/caddy/Caddyfile.example",
        "infra/systemd/sir-saathi-api.service",
        "infra/monitoring/healthcheck.sh",
        "infra/docker-compose.yml",
    ]:
        assert (ROOT / rel).is_file()


def test_systemd_service_uses_localhost_only() -> None:
    service = (ROOT / "infra/systemd/sir-saathi-api.service").read_text(encoding="utf-8")
    assert "--host 127.0.0.1" in service
    assert "NoNewPrivileges=true" in service
