# API And Database MVP

The first API surface is intentionally small and served under the `/api` prefix:

- `GET /api/health`
- `GET /api/states`
- `GET /api/forms`
- `POST /api/guidance`
- `POST /api/search`

Name search fails closed unless the request is explicitly using the sanitized pilot fixture or a future state has passed public launch readiness. Public search must be scoped by Assembly Constituency; `part_number` can only narrow a search when `ac_number` is also present.

The production adapter in `services/api/search_backend.py` reads PostgreSQL only after the state, abuse-verification, and rate-limit gates pass. Its query joins `public_search_scopes`, so it can read only an exact roll-version and versioned-AC combination that is enabled with reviewer identity and timestamp. Ingestion and readiness commands never create or enable allowlist rows. If `SIR_SAATHI_DATABASE_URL` is absent, no real search backend is configured and the API fails closed.

`GET /api/states` exposes canonical state metadata, including structured SIR schedule dates, CEO portal, official source labels, URLs, types, and `last_verified` dates so clients can show deadlines and source freshness.

`GET /api/forms` exposes the canonical SIR form catalogue and common document categories from `config/forms/sir-actions.json`.

The deployed `/api/search` handler also applies a fixed-window rate limit keyed by hashed client identity, state, and Assembly Constituency. This is intentionally small for the MVP and should move to a shared store before multi-process deployment.

API responses use redacted public records and do not expose full EPIC values, raw addresses, raw PDFs, or generated voter exports.

The PostgreSQL schema is in `db/schema.sql`; `db/migrations/0001_initial.sql` creates a fresh database, `0002_geography_provenance.sql` adds geographic source fields, `0003_transliterated_name_search.sql` indexes the derived Roman search form, and `0004_cross_year_match_candidates.sql` adds reviewable cross-year proposals.

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
