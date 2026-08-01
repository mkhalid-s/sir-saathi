# Deployment And Monitoring

## Target Shape

- Public origin: Caddy serves the built PWA and proxies `/api/*` on one HTTPS origin.
- API: VM running FastAPI on loopback behind Caddy.
- Database: PostgreSQL 16 with `pg_trgm`.
- Shared abuse limiter: secured Redis reachable only by the API.
- Monitoring: health endpoint checks and uptime monitor.
- Backups: encrypted database dumps or managed backups before public launch.

Use a current Caddy release that supports the standard `request_body max_size` directive, and run `caddy validate --config <candidate-Caddyfile>` before every reload. The template caps `/api/*` bodies at 16 KiB; the API independently enforces the same limit before JSON parsing, including for chunked or misleadingly declared bodies.

The same-origin topology is required by the browser client, which deliberately calls relative `/api/*` URLs. A CDN may proxy the complete public origin, but a static-only host must not be placed in front of the PWA unless it also routes `/api/*` to this Caddy origin without stripping the prefix.

## PWA Build

```sh
npm ci
ASTRO_TELEMETRY_DISABLED=1 npm run web:build
```

Build with Node 22. Set `PUBLIC_RELEASE_COMMIT` to the full lowercase 40-character Git commit and set `PUBLIC_TURNSTILE_SITE_KEY` to the public site key paired with the API's server-side secret and allowed production hostname. Configure the API with the identical commit in `SIR_SAATHI_RELEASE_COMMIT`. Publish the contents of `apps/web/dist` into a versioned, root-owned directory under `/srv/sir-saathi/web/releases`, then atomically point `/srv/sir-saathi/web/current` at that release. The Caddy service needs read and directory-traversal permission, but it must not own the release files. Validate the adapted Caddyfile before reloading Caddy.

Set `PUBLIC_SITE_URL` to the exact public HTTPS origin during every production build. It drives canonical links, reviewed-locale alternates, `sitemap.xml`, and `robots.txt`; the checked-in `.example` origin is only a deterministic local/CI default. Run `python scripts/check_discoverability.py --require-production-origin` after the production build so reserved example output cannot be deployed.

Package the reviewed static output into a deterministic, commit-bound bundle rather than copying a mutable working directory:

```sh
python -m pipeline.sir_saathi_pipeline.release_bundle \
  --create apps/web/dist \
  --output "reports/sir-saathi-web-${PUBLIC_RELEASE_COMMIT}.tar.gz" \
  --expected-commit "$PUBLIC_RELEASE_COMMIT"

python -m pipeline.sir_saathi_pipeline.release_bundle \
  --verify "reports/sir-saathi-web-${PUBLIC_RELEASE_COMMIT}.tar.gz" \
  --expected-commit "$PUBLIC_RELEASE_COMMIT"
```

Creation refuses symlinks and overwrites, verifies the 41-route release manifest against the HTML, records every static file's size and SHA-256 digest, normalizes archive metadata, writes atomically, and then independently reopens and verifies the result. Verification rejects unsafe archive paths, unexpected files, type changes, digest mismatches, corrupt compression, wrong commits, and oversized bundles without extracting content. Its redacted report contains the release commit, bundle digest, byte/file counts, and no file content. After verification, extract into a new empty staging directory, make the resulting `web/` tree root-owned and non-writable by Caddy, promote it under `/srv/sir-saathi/web/releases/<commit>`, and atomically repoint `current`; never extract directly over the active release.

The manually dispatched `Attested PWA release artifact` workflow requires the final origin and public Turnstile site key, reruns the launch gate, performs the production build, enforces production discoverability, creates and verifies the deterministic bundle, retains it for 30 days, and generates GitHub build provenance. GitHub's [artifact attestation guidance](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations) requires the workflow's OIDC and attestation permissions and supports verification with `gh attestation verify`. An attestation binds bytes to a repository, workflow, and commit; it does not replace this application's tests, review, authorization, or local digest verification.

Run the read-only, value-redacting production preflight in the same environment used for the release. Both modes require the final build and monitor origins plus the public/API release commits to match. Guidance-only deployment checks five fields. Indexed-search mode additionally requires `SIR_SAATHI_DEPLOYMENT_MODE=indexed-search` and validates the PostgreSQL/Redis URLs, distinct Turnstile public/server values, exact Turnstile hostname, trusted proxy hops, and private encrypted-backup destination/recipient:

```sh
python -m pipeline.sir_saathi_pipeline.deployment_preflight --mode guidance
python -m pipeline.sir_saathi_pipeline.deployment_preflight --mode indexed-search
```

Passing indexed-search preflight proves configuration shape only. It does not enable a state or scope, contact dependencies, verify a backup, replace migration checks, or grant launch authorization.

After the candidate release is deployed, audit the real public surface:

```sh
python -m pipeline.sir_saathi_pipeline.deployment_probe \
  --origin "$PUBLIC_SITE_URL" \
  --expected-commit "$PUBLIC_RELEASE_COMMIT"
```

The value-redacting probe checks 89 contracts. It verifies that the final URL stays on the requested HTTPS origin; the homepage identifies the PWA; required browser-security headers and deny-by-default/Turnstile CSP directives are present; the generated inner policy contains SHA-256 script/style hashes without `unsafe-inline`; `/api/health`, `/api/ready`, and `/api/version` are same-origin no-store JSON; readiness is green for the selected runtime mode; and the PWA and API expose the same expected release commit. The build-generated, no-cache release manifest must be bound to that commit and contain exactly the five core routes and all 36 state/UT routes. The probe fetches those 41 routes with bounded concurrency and requires each same-origin HTML response to match its manifest SHA-256 digest. An unknown route must also return the no-index HTML recovery page with HTTP 404. Reports contain stable check IDs rather than response bodies, redirect destinations, or network exception details; the verified Git commit is deliberately included as non-secret release evidence. Passing the probe is deployed-release evidence, but is not a substitute for the browser, accessibility, backup/restore, or indexed-search rehearsal.

## Guidance-Only Production Rehearsal

Create one private evidence record for the candidate commit before the first public guidance release. Templates created inside the repository are restricted to ignored `reports/` or `data/` paths; an operator-owned path outside the repository is also supported:

```sh
python -m pipeline.sir_saathi_pipeline.deployment_rehearsal \
  --create-template --output reports/deployment-rehearsal.json

python -m pipeline.sir_saathi_pipeline.deployment_rehearsal \
  --validate reports/deployment-rehearsal.json --require-full-pass
```

The schema-v2 template starts unapproved and requires a real HTTPS origin, the exact full deployed commit, the successful 89-check deployment-probe report bound to that commit, distinct operator and reviewer identities, explicit attestations that no voter data was used and public indexed search remained disabled, and evidence for all 11 build, database, edge, offline, backup/restore, monitoring, accessibility, and rollback checks. A failed check needs a remediation reference and passing retest. Validator output contains only stable blocker IDs and counts; it does not echo the origin, people, infrastructure details, or private evidence notes. This record proves rehearsal completeness, not public-search authorization or accessibility conformance.

## API Smoke Check

```sh
python -m pip install -r requirements.lock
uvicorn services.api.app:create_configured_app --factory --host 127.0.0.1 --port 8000
curl -fsS http://127.0.0.1:8000/api/health
curl -fsS http://127.0.0.1:8000/api/ready
```

Deploy the reviewed `requirements.lock`, not a freshly resolved `requirements.txt`, so CI and the VM run the same Python dependency graph.

CI also starts an empty disposable PostgreSQL 16 service and runs `scripts/check_postgres_integration.py`. The check first proves all eight migrations are pending, applies them through the production migration runner, proves the follow-up plan is clean, verifies `pg_trgm` and the required tables, and exercises the independently reviewed enable constraint and append-only authorization-event trigger with synthetic jurisdiction metadata. It asserts that the voter table remains empty and emits only stable redacted results. This is real schema-execution evidence on PostgreSQL 16; it does not replace the production migration dry run, pre-migration backup, restore drill, or operator review.

Before restarting a release, inspect the schema plan and then apply it explicitly:

```sh
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" python -m pipeline.sir_saathi_pipeline.migrations
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" python -m pipeline.sir_saathi_pipeline.migrations --apply
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" python -m pipeline.sir_saathi_pipeline.migrations --check
```

The runner expands the reviewed initial schema, records a SHA-256 checksum for every migration, rejects changed or unknown history, holds a PostgreSQL advisory lock across the operation, and applies each pending file in its own transaction. It never prints the database URL. Take and verify a recoverable backup before `--apply`; schema rollback remains restore/release-specific and is not inferred automatically.

## Encrypted Database Backups

Install PostgreSQL 16 client tools and `age` on the operator host. Choose an absolute backup directory outside the repository, owned by the backup operator and mode `0700`. Create an `age` recipient/identity pair using the deployment's secret-management process; the identity file must never enter Git or the application VM release directory.

```sh
SIR_SAATHI_DATABASE_URL="<operator-owned connection>" \
SIR_SAATHI_BACKUP_DIR="/secure/off-host/sir-saathi" \
SIR_SAATHI_AGE_RECIPIENT="<age recipient>" \
python -m pipeline.sir_saathi_pipeline.backups create

SIR_SAATHI_AGE_IDENTITY_FILE="/secure/keys/sir-saathi-backup-identity" \
python -m pipeline.sir_saathi_pipeline.backups verify \
  --backup "/secure/off-host/sir-saathi/<backup>.dump.age"
```

Creation streams `pg_dump` custom-format output directly into `age`; no plaintext archive is written. The command atomically promotes a non-empty encrypted artifact, writes a private SHA-256 sidecar, removes partial output on failure, and reports only the filename, checksum, and size—not the connection or voter data. Verification checks the encrypted checksum, decrypts as a stream, and asks `pg_restore --list` to validate archive structure without writing plaintext or connecting to a database.

Archive verification is not a restore drill. Before public indexed search, restore a reviewed backup into a newly created isolated PostgreSQL 16 database with no public network route, run migrations with `--check`, compare aggregate row/readiness counts, record the operator/date/result outside the repository, and securely destroy the drill database. PostgreSQL archives can execute source-controlled database definitions during restore, so use only backups produced by the trusted deployment and a least-privileged isolated target.

Real indexed search additionally requires runtime secrets/configuration outside Git: `SIR_SAATHI_RELEASE_COMMIT`, `SIR_SAATHI_DEPLOYMENT_MODE=indexed-search`, `SIR_SAATHI_DATABASE_URL`, `SIR_SAATHI_REDIS_URL`, `SIR_SAATHI_TURNSTILE_SECRET`, `SIR_SAATHI_TURNSTILE_HOSTNAME`, and the exact `SIR_SAATHI_TRUSTED_PROXY_HOPS` value. The configured application factory loads all seven. Guidance is the safe default and deliberately stays ready without search dependencies. `PUBLIC_RELEASE_COMMIT` and `PUBLIC_TURNSTILE_SITE_KEY` are intentionally public and belong in the PWA build environment; the Turnstile secret must never use the `PUBLIC_` prefix. Keep Uvicorn on loopback so untrusted clients cannot bypass Caddy or forge trusted forwarding headers.

## Local Database

`infra/docker-compose.yml` is for local development only. It binds PostgreSQL and Redis to `127.0.0.1`; PostgreSQL reads its database secret from an ignored file at `infra/.secrets/pg_secret`. A production Redis deployment must require authentication and transport security appropriate to its network.

## VM Services

- Use `infra/systemd/sir-saathi-api.service` as the API service template.
- Use `infra/caddy/Caddyfile.example` as the reverse proxy template.
- Replace the example hostname, keep the PWA root at `/srv/sir-saathi/web/current`, and keep `/api/*` on that exact origin. Caddy serves Astro's generated directory indexes and retains the API prefix when proxying.
- Preserve the template's HSTS, anti-framing, content-type, referrer, permissions, cross-origin-resource, and Content Security Policy header. The header is deny-by-default, retains header-only `frame-ancestors`, and allows network script/frame access only to Turnstile. Astro also emits an earlier per-page meta policy whose SHA-256 hashes bind every inline hydration script and generated style. Browsers enforce both policies, so the outer header's compatibility allowance cannot authorize un-hashed inline content. The generated CSP audit recomputes every inline hash, rejects inline event/style attributes and unapproved origins, and must pass after each production build.
- Create `/etc/sir-saathi/api.env` as `root:sir-saathi` with mode `0640`. Put the seven server-owned `SIR_SAATHI_*` values listed above in that file; never add `PUBLIC_RELEASE_COMMIT`, `PUBLIC_TURNSTILE_SITE_KEY`, or shell `export` syntax. The systemd unit loads this exact file before starting the API.
- Keep runtime configuration outside Git. After changing it, run `systemctl daemon-reload` when the unit changed and restart `sir-saathi-api`.

## Monitoring

Run `infra/monitoring/healthcheck.sh` from cron or an external uptime service. Its default API probe is the loopback `/api/ready` route and every request has a 10-second timeout; this detects indexed-search dependency loss while leaving guidance-mode availability independent. `WEB_URL` is required and must be the deployed public HTTPS origin so the probe exercises Caddy, TLS, and the PWA together; optionally override `API_URL` and `CURL_TIMEOUT_SECONDS`. Use the fuller deployment probe after releases and edge-policy changes rather than on a high-frequency uptime interval. Alert on API readiness failure, PWA failure, disk pressure, missing/failed encrypted backups, failed archive verification, overdue restore drills, and elevated error rates.

The API emits `public_search_event=<stable-id>` for search completion, rejection, rate limiting, limiter loss, and backend loss. Aggregate these IDs into rates and alerts; do not enable HTTP body/debug logging or enrich these events with query text, query prefixes, client addresses/hashes, Turnstile tokens, result counts, exception details, or voter records. Restrict and retain application logs according to the deployment's approved privacy and incident-response policy.

After every edge-policy change, inspect a deployed state page and exercise the indexed-search challenge in a browser with the console open. Treat CSP violations involving same-origin Astro assets or `https://challenges.cloudflare.com` as release blockers; do not broaden the policy to arbitrary third-party origins.

The `Official source freshness` GitHub Actions workflow runs every day at 08:47 IST and can also be started manually. It fails when any governed source exceeds its risk-based freshness window and retains the non-sensitive JSON report for 30 days even when the check fails. Treat a failed run as an editorial incident: review the linked official source, update `last_verified` only after a human confirms it, run the launch gate, and record the evidence in review. Configure repository Actions-failure notifications or an external alert route so a red scheduled run is not dependent on someone visiting the Actions page. Scheduled workflows run from the default branch, so this monitor becomes active only after the workflow reaches that branch.

## Rollback

1. Revert to the last known good Git commit.
2. Re-verify the retained bundle and commit identity for the last known good PWA release, then atomically repoint `/srv/sir-saathi/web/current` to its existing immutable directory.
3. Restart API service from the previous release directory.
4. Restore database only from verified backups when schema/data changes require it.
