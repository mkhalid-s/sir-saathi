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


def test_caddy_routes_api_prefix_without_stripping() -> None:
    caddy = (ROOT / "infra/caddy/Caddyfile.example").read_text(encoding="utf-8")
    assert "handle /api/*" in caddy
    assert "reverse_proxy 127.0.0.1:8000" in caddy
    assert "Cache-Control" in caddy


def test_compose_is_local_only_and_not_trust_auth() -> None:
    compose = (ROOT / "infra/docker-compose.yml").read_text(encoding="utf-8")
    assert "Local development only" in compose
    assert '"127.0.0.1:5432:5432"' in compose
    assert "POSTGRES_HOST_AUTH_METHOD" not in compose
    assert "POSTGRES_PASSWORD_FILE" in compose
