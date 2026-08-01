# API And Database MVP

The first API surface is intentionally small and served under the `/api` prefix:

- `GET /api/health`
- `GET /api/ready`
- `GET /api/states`
- `GET /api/forms`
- `POST /api/guidance`
- `POST /api/search`

`GET /api/states?locale=<code>`, `GET /api/forms?locale=<code>`, and the optional `locale` field on `POST /api/guidance` use the same reviewed catalogue as the PWA. Human-readable display fields are translated only when the requested locale is publishable. Responses include `locale_requested`, `locale_used`, and `locale_fallback`; planned, unknown, incomplete, or unreviewed locales visibly fall back to English. Stable state IDs, capability codes, dates, URLs, and source evidence remain language-neutral or verbatim.

Name search fails closed unless a future state has passed public launch readiness. The pure `search_payload` test/local-demo harness can explicitly use the sanitized pilot fixture, but the deployed `POST /api/search` route rejects that client-controlled flag so it cannot bypass server-owned launch controls. Public search must be scoped by Assembly Constituency; `part_number` can only narrow a search when `ac_number` is also present.

The production adapter in `services/api/search_backend.py` reads PostgreSQL only after the state, abuse-verification, and rate-limit gates pass. Its query joins `public_search_scopes`, so it can read only an exact roll-version and versioned-AC combination that is enabled with distinct operator/reviewer identities and a timestamp. Every authorization change also appends a `public_search_scope_events` row with both identities, its rationale, and aggregate readiness snapshot. Ingestion and readiness commands never create or enable allowlist rows. If `SIR_SAATHI_DATABASE_URL` is absent, no real search backend is configured and the API fails closed.

`GET /api/states` exposes canonical state metadata, including structured SIR schedule dates, CEO portal, official source labels, URLs, types, and `last_verified` dates so clients can show deadlines and source freshness.

`GET /api/forms` exposes the canonical SIR form catalogue and common document categories from `config/forms/sir-actions.json`.

`GET /api/health` is process liveness. `GET /api/ready` is deployment-mode-aware readiness: guidance mode does not depend on indexed-search infrastructure, while indexed-search mode returns HTTP 503 unless server-side Turnstile is configured, PostgreSQL answers a data-free `SELECT 1`, the shared Redis limiter answers a non-mutating `PING`, and the trusted proxy boundary is configured. Readiness reports stable blocker IDs and never returns connection strings or exception details.

The deployed `/api/search` handler checks launch policy and a hashed, client-global verification-attempt limit before calling the external challenge verifier. A separate fixed-window search limit uses the same client-global scope across all states and Assembly Constituencies, preventing invalid-token floods and scope rotation from resetting their respective allowances. Production indexed search requires the atomic shared Redis implementation; missing or unavailable Redis fails closed.

API responses use redacted public records and do not expose full EPIC values, raw addresses, raw PDFs, or generated voter exports.

The PostgreSQL schema is in `db/schema.sql`; ordered files in `db/migrations` are applied only through `python -m pipeline.sir_saathi_pipeline.migrations`. The command is dry-run-first, pins applied checksums in `schema_migrations`, rejects rewritten or unknown history, serializes concurrent operators with an advisory lock, and applies each pending file transactionally. `--apply` is explicit and `--check` is suitable for a deployment gate.

Before loading rolls, seed canonical state rows from `config/states` into local Postgres:

```bash
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.seed_states
```

The state seed command is local-only and idempotent. It upserts only the `states` table from reviewed config fields, including `public_launch_ready` exactly as configured, so later roll loads can satisfy foreign-key checks without inventing state metadata.

Before parsing a local PDF, validate a reviewed source manifest entry:

```bash
python -m pipeline.sir_saathi_pipeline.sources --manifest data/local/sources.json --source-id <source-id> --verify-file
```

The source manifest records reviewed metadata such as state, roll year, roll kind, source label, official source URI, local ignored PDF path, `sha256:<64 lowercase hex>` checksum, parser hint, and language. The validator requires `reviewed: true`, a repo-relative `local_path` under ignored `data/` or `samples/`, a checksum match when `--verify-file` is used, and a registered parser whose state/roll-kind scope and ingestion-readiness status pass. `parse_2002` is currently ready only for reviewed Maharashtra historical/base-roll inputs. `maharashtra_current_unicode_v1` is synthetic-fixture-only and remains blocked until an authorized official current-roll sample passes record-accounting and layout validation.

Operators can draft a manifest entry from a local ignored PDF without marking it reviewed:

```bash
python -m pipeline.sir_saathi_pipeline.sources --draft --source-id <source-id> --state IN-MH --roll-year 2002 --roll-kind historical_base_roll --source-label "<official source label>" --source-uri "<official PDF URL>" --local-path data/local/<file>.pdf --language mr --output-manifest data/local/sources.json
```

The draft command computes the local file checksum and prints a JSON entry with `reviewed: false`, `valid_for_ingestion: false`, and a review-required note. With `--output-manifest`, it creates or appends to a local ignored manifest under `data/` or `samples/`, rejects duplicate `source_id` values, and still keeps the entry unreviewed. A human must verify the official source metadata and set `reviewed: true` in the local manifest before the validator or operator workflow will allow ingestion.

Operators can generate a local review report before changing `reviewed`:

```bash
python -m pipeline.sir_saathi_pipeline.sources --review --manifest data/local/sources.json --source-id <source-id> --verify-file
```

The review report checks required fields, parser hint, ignored local paths, checksum format, and local checksum match. It can report `ready_for_human_review: true` for a complete draft while keeping `valid_for_ingestion: false` until a human explicitly sets `reviewed: true`.

Parsed roll ingestion starts as a local-only staging mapper in `pipeline/sir_saathi_pipeline/ingestion.py`. It converts parser output into DB-shaped rows for districts, versioned Assembly Constituency snapshots, polling stations, source documents, roll versions, extraction runs, and voter records; validates parsed counts against source metadata; normalizes names for search; and stores EPIC only as a hash plus last four characters. Reviewed parser metadata can supply `district_name`, `district_code`, `geography_source_label`, `geography_source_updated_at`, and `geography_version`. Without a reviewed geography version, ingestion uses a roll-year snapshot identifier so a historical AC number can never overwrite a current constituency with the same number. If district metadata is absent, ingestion remains backward compatible and does not invent a district relationship. It does not download PDFs, write raw exports, connect to Postgres, or enable public indexed search by itself.

Local PDF ingestion can be validated with a dry run:

```bash
SIR_SAATHI_EPIC_HASH_SALT="local-only-secret" python -m pipeline.sir_saathi_pipeline.ingest_roll --pdf data/local/<file>.pdf --state IN-MH --parser-hint parse_2002 --dry-run
```

The dry-run command computes the PDF checksum, optionally compares it with `--expected-checksum` from the reviewed source manifest before parsing, calls the 2002 parser, builds an ingestion batch, and prints a safe JSON report with AC/part metadata, expected and parsed record counts, quality summary, and DB row counts. It requires `--dry-run` and `SIR_SAATHI_EPIC_HASH_SALT`, and its report does not include raw EPIC values, voter names, local file paths, CSV exports, JSON voter exports, or database writes.

After a dry run passes, the same validated batch can be loaded into local Postgres with an explicit `--load`:

```bash
SIR_SAATHI_EPIC_HASH_SALT="local-only-secret" SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.ingest_roll --pdf data/local/<file>.pdf --state IN-MH --load
```

The loader uses a transaction and idempotent `INSERT ... ON CONFLICT ... DO UPDATE` statements. It requires the target `states` row to already exist, then loads an optional reviewed district before its AC, polling station, roll version, source document, extraction run, and voter rows. The load summary is safe JSON with counts and checksum only; it does not enable public search, change `public_launch_ready`, write generated voter exports, or expose raw EPIC values in output.

Local loaded-roll search can be validated against Postgres without exposing the public API:

```bash
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.local_search --state IN-MH --ac 172 --name "<name to test>"
```

The local search validator uses `pg_trgm` similarity across the source-normalized and explicitly derived Roman name forms, requires state and Assembly Constituency scope, caps results, and prints timing plus redacted match fields. Legacy VirgoD3 conversion is used only when parser metadata declares that encoding; ingestion does not guess legacy encodings. It reports `safe_for_public: false`, does not print the raw query, excludes `epic_hash`, hides `epic_last4` unless explicitly requested with `--include-epic-last4`, and does not change `/api/search` launch behavior.

Cross-year comparison in `pipeline/sir_saathi_pipeline/cross_year_matching.py` is local-only candidate generation. It requires matching state, AC, and an explicit `reviewed:` geography-equivalence scope; a reused AC number alone is never treated as the same place. Part continuity contributes only through a separately reviewed part-equivalence scope. It considers name/native-Roman forms, relative name, expected age progression, gender, and reviewed geography, and caps candidates per current record. It never marks a proposal confirmed. The database permits `confirmed` or `rejected` only with reviewer identity and timestamp, while the safe report exposes aggregate score bands and ambiguity counts without names or record identifiers. Candidate scores must not be used as voter-eligibility decisions.

Loaded data readiness can be checked with a local operator report:

```bash
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.readiness_report --state IN-MH --ac 172
```

The readiness report summarizes source documents, extraction runs, expected versus parsed counts, scoped voter-record counts, data-quality issue rates, and state configuration gates such as schedule provenance and `public_launch_ready`. It outputs safe JSON only, includes blockers, defaults `ready_for_public` to false unless all strict criteria pass, and never returns voter rows or changes public search settings.

Operators can generate the full local onboarding workflow for one state/AC/PDF:

```bash
python -m pipeline.sir_saathi_pipeline.operator_workflow --state IN-MH --ac 172 --part 21 --pdf data/local/<file>.pdf --manifest data/local/sources.json --source-id <source-id>
```

The workflow planner prints the safe command sequence for state seeding, source manifest validation, PDF dry-run, explicit load, local search validation, and readiness reporting. It does not execute the commands, does not print a raw test name, keeps search names in `SIR_SAATHI_TEST_NAME`, and should be run before considering any public-search work.

### Audited exact-scope authorization

Exact public-search scopes are managed with a separate operator command. It
checks the exact state, roll version, versioned AC, source/extraction accounting,
scoped voter counts, issue rate, official provenance, indexed-search capability,
and state launch flag. Its output contains aggregate counts only. Inspection does
not write anything:

```bash
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.public_search_scope --state IN-MH --ac 172 --roll-version-id <roll-id> --ac-id <versioned-ac-id>
```

`--enable` and `--disable` both require accountable operator and reviewer identifiers and a
non-empty reason. They still default to a dry run; `--apply` is the separate,
explicit mutation switch. The applied readiness check, append-only event, and
allowlist update run in one serializable transaction. Enable fails closed on any
blocker; disable remains available when launch or data readiness has degraded.

```bash
# Preview, with no database write
python -m pipeline.sir_saathi_pipeline.public_search_scope --state IN-MH --ac 172 --roll-version-id <roll-id> --ac-id <versioned-ac-id> --enable --operated-by <operator-id> --reviewed-by <different-reviewer-id> --reason "<approval record>"

# Apply only after the preview and independent human approval
python -m pipeline.sir_saathi_pipeline.public_search_scope --state IN-MH --ac 172 --roll-version-id <roll-id> --ac-id <versioned-ac-id> --enable --operated-by <operator-id> --reviewed-by <different-reviewer-id> --reason "<approval record>" --apply

# Emergency or planned revocation
python -m pipeline.sir_saathi_pipeline.public_search_scope --state IN-MH --ac 172 --roll-version-id <roll-id> --ac-id <versioned-ac-id> --disable --operated-by <operator-id> --reviewed-by <reviewer-id> --reason "<revocation record>" --apply
```

Do not place voter names, EPIC values, addresses, or search strings in
`--reason`. Enabling the database scope is necessary but not sufficient: the API
also continues to require the reviewed state launch flag, Turnstile, and shared
rate limiting. No state config or database scope is automatically promoted by
ingestion.
