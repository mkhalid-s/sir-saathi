# Deployment And Monitoring

## Target Shape

- PWA: Cloudflare Pages from `apps/web`.
- API: VM running FastAPI behind Caddy under `/api/*`.
- Database: PostgreSQL 16 with `pg_trgm`.
- Shared abuse limiter: secured Redis reachable only by the API.
- Monitoring: health endpoint checks and uptime monitor.
- Backups: encrypted database dumps or managed backups before public launch.

## PWA Build

```sh
npm ci
ASTRO_TELEMETRY_DISABLED=1 npm run web:build
```

Cloudflare Pages settings:

- Build command: `npm run web:build`
- Build output directory: `apps/web/dist`
- Node version: `22`
- Build variable: `PUBLIC_TURNSTILE_SITE_KEY` set to the public site key paired with the API's server-side secret and allowed production hostname.

## API Smoke Check

```sh
python -m pip install -r requirements.lock
uvicorn services.api.app:create_configured_app --factory --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/api/health
```

Deploy the reviewed `requirements.lock`, not a freshly resolved `requirements.txt`, so CI and the VM run the same Python dependency graph.

Real indexed search additionally requires runtime secrets/configuration outside Git: `SIR_SAATHI_DATABASE_URL`, `SIR_SAATHI_REDIS_URL`, `SIR_SAATHI_TURNSTILE_SECRET`, `SIR_SAATHI_TURNSTILE_HOSTNAME`, and the exact `SIR_SAATHI_TRUSTED_PROXY_HOPS` value. The configured application factory loads all five. `PUBLIC_TURNSTILE_SITE_KEY` is intentionally public and belongs in the PWA build environment; the Turnstile secret must never use the `PUBLIC_` prefix. Keep Uvicorn on loopback so untrusted clients cannot bypass Caddy or forge trusted forwarding headers.

## Local Database

`infra/docker-compose.yml` is for local development only. It binds PostgreSQL and Redis to `127.0.0.1`; PostgreSQL reads its database secret from an ignored file at `infra/.secrets/pg_secret`. A production Redis deployment must require authentication and transport security appropriate to its network.

## VM Services

- Use `infra/systemd/sir-saathi-api.service` as the API service template.
- Use `infra/caddy/Caddyfile.example` as the reverse proxy template.
- Create `/etc/sir-saathi/api.env` as `root:sir-saathi` with mode `0640`. Put the five server-owned `SIR_SAATHI_*` values listed above in that file; never add `PUBLIC_TURNSTILE_SITE_KEY` or shell `export` syntax. The systemd unit loads this exact file before starting the API.
- Keep runtime configuration outside Git. After changing it, run `systemctl daemon-reload` when the unit changed and restart `sir-saathi-api`.

## Monitoring

Run `infra/monitoring/healthcheck.sh` from cron or an external uptime service. Its default API probe is the deployed `/api/health` route and every request has a 10-second timeout. Set `API_URL`, `WEB_URL`, and optionally `CURL_TIMEOUT_SECONDS` for the deployment. Alert on API health failure, PWA failure, disk pressure, database backup failure, and elevated error rates.

The `Official source freshness` GitHub Actions workflow runs every day at 08:47 IST and can also be started manually. It fails when any governed source exceeds its risk-based freshness window and retains the non-sensitive JSON report for 30 days even when the check fails. Treat a failed run as an editorial incident: review the linked official source, update `last_verified` only after a human confirms it, run the launch gate, and record the evidence in review. Configure repository Actions-failure notifications or an external alert route so a red scheduled run is not dependent on someone visiting the Actions page. Scheduled workflows run from the default branch, so this monitor becomes active only after the workflow reaches that branch.

## Rollback

1. Revert to the last known good Git commit.
2. Rebuild the PWA and redeploy Cloudflare Pages.
3. Restart API service from the previous release directory.
4. Restore database only from verified backups when schema/data changes require it.
