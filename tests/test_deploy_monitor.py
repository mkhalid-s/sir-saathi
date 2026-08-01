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
        "requirements.lock",
        "pipeline/sir_saathi_pipeline/backups.py",
    ]:
        assert (ROOT / rel).is_file()


def test_systemd_service_uses_localhost_only() -> None:
    service = (ROOT / "infra/systemd/sir-saathi-api.service").read_text(encoding="utf-8")
    assert "--host 127.0.0.1" in service
    assert "EnvironmentFile=/etc/sir-saathi/api.env" in service
    assert "NoNewPrivileges=true" in service
    assert "ProtectSystem=strict" in service
    assert "CapabilityBoundingSet=" in service


def test_caddy_routes_api_prefix_without_stripping() -> None:
    caddy = (ROOT / "infra/caddy/Caddyfile.example").read_text(encoding="utf-8")
    assert "handle /api/*" in caddy
    assert "reverse_proxy 127.0.0.1:8000" in caddy
    assert "Cache-Control" in caddy


def test_caddy_serves_the_static_pwa_on_the_api_origin() -> None:
    caddy = (ROOT / "infra/caddy/Caddyfile.example").read_text(encoding="utf-8")

    assert "root * /srv/sir-saathi/web/current" in caddy
    assert "file_server" in caddy
    assert "PWA is served by Cloudflare Pages" not in caddy
    assert "path /sw.js /manifest.webmanifest" in caddy
    assert 'Cache-Control "no-cache"' in caddy


def test_caddy_enforces_browser_security_headers_with_turnstile_allowlist() -> None:
    caddy = (ROOT / "infra/caddy/Caddyfile.example").read_text(encoding="utf-8")

    for header in [
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
        "Permissions-Policy",
        "Cross-Origin-Resource-Policy",
        "Content-Security-Policy",
    ]:
        assert header in caddy
    assert "default-src 'none'" in caddy
    assert "frame-ancestors 'none'" in caddy
    assert "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com" in caddy
    assert "connect-src 'self' https://challenges.cloudflare.com" in caddy
    assert "frame-src https://challenges.cloudflare.com" in caddy


def test_compose_is_local_only_and_not_trust_auth() -> None:
    compose = (ROOT / "infra/docker-compose.yml").read_text(encoding="utf-8")
    assert "Local development only" in compose
    assert '"127.0.0.1:5432:5432"' in compose
    assert "POSTGRES_HOST_AUTH_METHOD" not in compose
    assert "POSTGRES_PASSWORD_FILE" in compose


def test_healthcheck_probes_the_deployed_api_route_with_a_timeout() -> None:
    healthcheck = (ROOT / "infra/monitoring/healthcheck.sh").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000/api/health" in healthcheck
    assert "127.0.0.1:8000/health" not in healthcheck
    assert "--max-time" in healthcheck
    assert 'WEB_URL="${WEB_URL:-}"' in healthcheck
    assert "WEB_URL must be set" in healthcheck


def test_ci_and_deployment_use_the_exact_python_lock() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    dependencies = [line for line in lock.splitlines() if line and not line.startswith("#")]
    assert "pip install -r requirements.lock" in workflow
    assert dependencies
    assert all("==" in dependency for dependency in dependencies)
    assert any(dependency.startswith("fastapi==") for dependency in dependencies)
    assert any(dependency.startswith("psycopg-binary==") for dependency in dependencies)
    assert any(dependency.startswith("redis==") for dependency in dependencies)


def test_backup_operator_path_is_encrypted_and_non_destructive() -> None:
    backup = (ROOT / "pipeline/sir_saathi_pipeline/backups.py").read_text(encoding="utf-8")

    assert '"PGDATABASE": database_url' in backup
    assert '"--format=custom"' in backup
    assert '"--encrypt", "--recipient"' in backup
    assert '"--decrypt", "--identity"' in backup
    assert '"--list"' in backup
    assert "plaintext_written_to_disk" in backup
    assert "backup directory must stay outside the repository" in backup
