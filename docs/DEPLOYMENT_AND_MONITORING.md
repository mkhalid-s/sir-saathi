# Deployment And Monitoring

## Target Shape

- PWA: Cloudflare Pages from `apps/web`.
- API: VM running FastAPI behind Caddy under `/api/*`.
- Database: PostgreSQL 16 with `pg_trgm`.
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

## API Smoke Check

```sh
uvicorn services.api.app:create_app --factory --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/api/health
```

## Local Database

`infra/docker-compose.yml` is for local development only. It binds PostgreSQL to `127.0.0.1` and reads the database secret from an ignored file at `infra/.secrets/pg_secret`.

## VM Services

- Use `infra/systemd/sir-saathi-api.service` as the API service template.
- Use `infra/caddy/Caddyfile.example` as the reverse proxy template.
- Keep runtime configuration outside Git.

## Monitoring

Run `infra/monitoring/healthcheck.sh` from cron or an external uptime service. Alert on API health failure, PWA failure, disk pressure, database backup failure, and elevated error rates.

## Rollback

1. Revert to the last known good Git commit.
2. Rebuild the PWA and redeploy Cloudflare Pages.
3. Restart API service from the previous release directory.
4. Restore database only from verified backups when schema/data changes require it.
