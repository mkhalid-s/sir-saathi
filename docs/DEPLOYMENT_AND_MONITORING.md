# Deployment And Monitoring

## Target Shape

- Public origin: Caddy serves the built PWA and proxies `/api/*` on one HTTPS origin.
- API: VM running FastAPI on loopback behind Caddy.
- Database: PostgreSQL 16 with `pg_trgm`.
- Shared abuse limiter: secured Redis reachable only by the API.
- Monitoring: health endpoint checks and uptime monitor.
- Backups: encrypted database dumps or managed backups before public launch.

The same-origin topology is required by the browser client, which deliberately calls relative `/api/*` URLs. A CDN may proxy the complete public origin, but a static-only host must not be placed in front of the PWA unless it also routes `/api/*` to this Caddy origin without stripping the prefix.

## PWA Build

```sh
npm ci
ASTRO_TELEMETRY_DISABLED=1 npm run web:build
```

Build with Node 22 and set `PUBLIC_TURNSTILE_SITE_KEY` to the public site key paired with the API's server-side secret and allowed production hostname. Publish the contents of `apps/web/dist` into a versioned, root-owned directory under `/srv/sir-saathi/web/releases`, then atomically point `/srv/sir-saathi/web/current` at that release. The Caddy service needs read and directory-traversal permission, but it must not own the release files. Validate the adapted Caddyfile before reloading Caddy.

Set `PUBLIC_SITE_URL` to the exact public HTTPS origin during every production build. It drives canonical links, reviewed-locale alternates, `sitemap.xml`, and `robots.txt`; the checked-in `.example` origin is only a deterministic local/CI default. Run `python scripts/check_discoverability.py --require-production-origin` after the production build so reserved example output cannot be deployed.

## API Smoke Check

```sh
python -m pip install -r requirements.lock
uvicorn services.api.app:create_configured_app --factory --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/api/health
```

Deploy the reviewed `requirements.lock`, not a freshly resolved `requirements.txt`, so CI and the VM run the same Python dependency graph.

Before restarting a release, inspect the schema plan and then apply it explicitly:

```sh
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" python -m pipeline.sir_saathi_pipeline.migrations
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" python -m pipeline.sir_saathi_pipeline.migrations --apply
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" python -m pipeline.sir_saathi_pipeline.migrations --check
```

The runner expands the reviewed initial schema, records a SHA-256 checksum for every migration, rejects changed or unknown history, holds a PostgreSQL advisory lock across the operation, and applies each pending file in its own transaction. It never prints the database URL. Take and verify a recoverable backup before `--apply`; schema rollback remains restore/release-specific and is not inferred automatically.

Real indexed search additionally requires runtime secrets/configuration outside Git: `SIR_SAATHI_DATABASE_URL`, `SIR_SAATHI_REDIS_URL`, `SIR_SAATHI_TURNSTILE_SECRET`, `SIR_SAATHI_TURNSTILE_HOSTNAME`, and the exact `SIR_SAATHI_TRUSTED_PROXY_HOPS` value. The configured application factory loads all five. `PUBLIC_TURNSTILE_SITE_KEY` is intentionally public and belongs in the PWA build environment; the Turnstile secret must never use the `PUBLIC_` prefix. Keep Uvicorn on loopback so untrusted clients cannot bypass Caddy or forge trusted forwarding headers.

## Local Database

`infra/docker-compose.yml` is for local development only. It binds PostgreSQL and Redis to `127.0.0.1`; PostgreSQL reads its database secret from an ignored file at `infra/.secrets/pg_secret`. A production Redis deployment must require authentication and transport security appropriate to its network.

## VM Services

- Use `infra/systemd/sir-saathi-api.service` as the API service template.
- Use `infra/caddy/Caddyfile.example` as the reverse proxy template.
- Replace the example hostname, keep the PWA root at `/srv/sir-saathi/web/current`, and keep `/api/*` on that exact origin. Caddy serves Astro's generated directory indexes and retains the API prefix when proxying.
- Preserve the template's HSTS, anti-framing, content-type, referrer, permissions, cross-origin-resource, and Content Security Policy headers. The CSP is deny-by-default and allows network script/frame access only to the Turnstile challenge origin. Astro's static hydration bootstrap and generated island styles are inline, so the reviewed policy currently contains `unsafe-inline` for scripts and styles; moving to build-generated hashes or runtime nonces is a tracked hardening improvement, not a reason to remove the rest of the allowlist.
- Create `/etc/sir-saathi/api.env` as `root:sir-saathi` with mode `0640`. Put the five server-owned `SIR_SAATHI_*` values listed above in that file; never add `PUBLIC_TURNSTILE_SITE_KEY` or shell `export` syntax. The systemd unit loads this exact file before starting the API.
- Keep runtime configuration outside Git. After changing it, run `systemctl daemon-reload` when the unit changed and restart `sir-saathi-api`.

## Monitoring

Run `infra/monitoring/healthcheck.sh` from cron or an external uptime service. Its default API probe is the loopback `/api/health` route and every request has a 10-second timeout. `WEB_URL` is required and must be the deployed public HTTPS origin so the probe exercises Caddy, TLS, and the PWA together; optionally override `API_URL` and `CURL_TIMEOUT_SECONDS`. Alert on API health failure, PWA failure, disk pressure, database backup failure, and elevated error rates.

After every edge-policy change, inspect a deployed state page and exercise the indexed-search challenge in a browser with the console open. Treat CSP violations involving same-origin Astro assets or `https://challenges.cloudflare.com` as release blockers; do not broaden the policy to arbitrary third-party origins.

The `Official source freshness` GitHub Actions workflow runs every day at 08:47 IST and can also be started manually. It fails when any governed source exceeds its risk-based freshness window and retains the non-sensitive JSON report for 30 days even when the check fails. Treat a failed run as an editorial incident: review the linked official source, update `last_verified` only after a human confirms it, run the launch gate, and record the evidence in review. Configure repository Actions-failure notifications or an external alert route so a red scheduled run is not dependent on someone visiting the Actions page. Scheduled workflows run from the default branch, so this monitor becomes active only after the workflow reaches that branch.

## Rollback

1. Revert to the last known good Git commit.
2. Atomically repoint `/srv/sir-saathi/web/current` to the last known good PWA release.
3. Restart API service from the previous release directory.
4. Restore database only from verified backups when schema/data changes require it.
