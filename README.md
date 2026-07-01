# SIR Saathi

SIR Saathi is a civic-tech prototype for helping people understand India's Special Intensive Revision (SIR) process and safely find the right next action. The project combines a mobile-first public PWA, a small `/api` surface, and a local-only electoral-roll ingestion pipeline that can parse, validate, load, and search reviewed roll data without exposing raw voter data publicly.

The current product direction is deliberately practical: guide users through official SIR steps, show source-backed state information, and build a privacy-conscious local data pipeline before enabling any public indexed search.

## Current Status

This repository is an MVP/prototype. It includes:

- A mobile-first Astro + Preact PWA in `apps/web`.
- A FastAPI service in `services/api`.
- Canonical state and forms configuration in `config`.
- A PostgreSQL schema and migration in `db`.
- Local-only PDF parsing, ingestion, loading, search validation, readiness reporting, and operator workflow tools in `pipeline`.
- Safety gates and sensitive-data checks in `scripts`.
- Product, API, privacy, launch, and operating docs in `docs`.

Public indexed search is intentionally fail-closed unless strict launch criteria are satisfied. Raw PDFs, parsed voter exports, full EPIC values, local databases, secrets, and generated reports are not committed.

## Product Features

### Mobile PWA

The web app is a mobile-first Progressive Web App. It currently provides:

- State selector backed by reviewed config in `config/states`.
- SIR deadline and source-freshness display.
- Safe "Find my name" entry flow that prioritizes official search steps before local indexed-search behavior.
- Situation-based guidance for verification, missing names, new voters, shifted addresses, corrections, deceased-family entries, duplicate entries, and portal failures.
- Follow-up questions for BLO visit, enumeration form receipt/submission, current-roll match, and base-roll match.
- Next-action checklist and WhatsApp-shareable checklist copy.
- Reminders to confirm official sources and avoid sharing private voter details.
- Forms and common document reference backed by `config/forms/sir-actions.json`.
- Search availability status that explains when indexed search is off and why.
- UI language readiness messaging. English is available; non-English UI translations are marked planned until human review.
- Installable PWA manifest, app icon, and offline app-shell service worker. API requests are not cached offline.

More detail: `docs/PWA_MVP.md`.

### API

The initial API is intentionally small and served under `/api`:

- `GET /api/health`
- `GET /api/states`
- `GET /api/forms`
- `POST /api/guidance`
- `POST /api/search`

The public search path is privacy-gated:

- Search must be scoped by Assembly Constituency.
- `part_number` can only narrow an already scoped AC search.
- Responses are redacted and do not expose full EPIC values, raw addresses, raw PDFs, or generated voter exports.
- Search applies a fixed-window rate limit keyed by hashed client identity, state, and AC.
- Public indexed search requires official schedule provenance and launch readiness.

More detail: `docs/API_AND_DB.md` and `docs/PRIVACY_AND_ABUSE.md`.

## Local Data Pipeline

The pipeline is designed for local operator use before any public launch decision. It supports:

- Legacy 2002 Maharashtra roll parsing via `pipeline/parse_2002.py`.
- VirgoD3 transliteration utilities via `pipeline/transliterate.py`.
- DB-ready ingestion mapping in `pipeline/sir_saathi_pipeline/ingestion.py`.
- Reviewed source manifest validation in `pipeline/sir_saathi_pipeline/sources.py`.
- Source manifest drafting with computed checksums, always `reviewed: false` until human review.
- Explicit dry-run and load commands in `pipeline/sir_saathi_pipeline/ingest_roll.py`.
- Idempotent local PostgreSQL loading in `pipeline/sir_saathi_pipeline/db_loader.py`.
- Local loaded-roll search validation in `pipeline/sir_saathi_pipeline/local_search.py`.
- Local readiness reports in `pipeline/sir_saathi_pipeline/readiness_report.py`.
- Local state seeding in `pipeline/sir_saathi_pipeline/seed_states.py`.
- Operator workflow planning in `pipeline/sir_saathi_pipeline/operator_workflow.py`.

The intended local flow is:

```sh
python -m pipeline.sir_saathi_pipeline.sources --draft --source-id <source-id> --state IN-MH --roll-year 2002 --roll-kind historical_base_roll --source-label "<official source label>" --source-uri "<official PDF URL>" --local-path data/local/<file>.pdf --language mr --output-manifest data/local/sources.json
python -m pipeline.sir_saathi_pipeline.sources --review --manifest data/local/sources.json --source-id <source-id> --verify-file
python -m pipeline.sir_saathi_pipeline.sources --manifest data/local/sources.json --source-id <source-id> --verify-file
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.seed_states
SIR_SAATHI_EPIC_HASH_SALT="local-only-secret" python -m pipeline.sir_saathi_pipeline.ingest_roll --pdf data/local/<file>.pdf --state IN-MH --dry-run
SIR_SAATHI_EPIC_HASH_SALT="local-only-secret" SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.ingest_roll --pdf data/local/<file>.pdf --state IN-MH --load
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.local_search --state IN-MH --ac 172 --name "<name to test>"
SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi" python -m pipeline.sir_saathi_pipeline.readiness_report --state IN-MH --ac 172
```

The workflow planner can print the full sequence without executing commands:

```sh
python -m pipeline.sir_saathi_pipeline.operator_workflow --state IN-MH --ac 172 --part 21 --pdf data/local/<file>.pdf --manifest data/local/sources.json --source-id <source-id>
```

## What Is Not Included

The MVP does not include:

- Native mobile apps.
- User accounts.
- Document uploads.
- Reminder subscriptions.
- National unscoped voter search.
- Bulk voter exports.
- Public raw PDF access.
- AI eligibility decisions.
- Full reviewed non-English UI translations.

AI may help explain source-backed guidance or summarize checklists, but it must not decide voter eligibility, invent deadlines, or process raw voter data by default.

## Setup

### Python

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Web

```sh
npm ci
npm run web:build
```

Run the web app locally:

```sh
npm run web:dev
```

### Optional Local Database

Use PostgreSQL 16 or compatible PostgreSQL with `pg_trgm` support. The schema is in `db/schema.sql`, with the initial migration in `db/migrations/0001_initial.sql`.

Local pipeline commands that write to or read from Postgres require:

```sh
export SIR_SAATHI_DATABASE_URL="postgresql://sir_saathi@127.0.0.1:5432/sir_saathi"
```

Ingestion also requires a local-only EPIC hash salt:

```sh
export SIR_SAATHI_EPIC_HASH_SALT="local-only-secret"
```

Do not commit local secrets or `.env` files.

## Validation

Common local checks:

```sh
python scripts/check_sensitive.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest
npm audit --workspace apps/web
npm run web:build
python scripts/launch_gate.py
python scripts/slice_gate.py
```

Parser and transliteration smoke checks:

```sh
python -m py_compile pipeline/parse_2002.py pipeline/transliterate.py
python pipeline/transliterate.py --test
```

## Privacy And Safety

Electoral rolls are public documents, but bulk voter data can still create privacy and misuse risks. This repository follows these rules:

- Raw electoral roll PDFs stay local under ignored paths such as `data/`.
- Parsed voter exports and validation datasets stay local.
- Full EPIC values are not exposed in public API responses.
- Local ingestion stores EPIC as a hash plus last four characters.
- Search reports are redacted and scoped.
- Public indexed search remains off unless launch readiness, official source provenance, and abuse-prevention gates pass.
- Checklists and share text must not include EPIC, address, phone, document, or other private voter details.

More detail: `docs/PRIVACY_AND_ABUSE.md`, `docs/GUIDANCE_RULES.md`, and `docs/LAUNCH_CHECKLIST.md`.

## Repository Map

```text
apps/web/                 Mobile-first Astro + Preact PWA
config/forms/             SIR forms and document catalogue
config/states/            Canonical state configuration
db/                       PostgreSQL schema and migrations
docs/                     Product, privacy, API, launch, and operating docs
infra/                    Deployment templates and infrastructure notes
pipeline/                 Parsers, ingestion, local search, readiness, workflow tools
scripts/                  Sensitive-data scan and validation gates
services/api/             FastAPI service and privacy policy enforcement
tests/                    Python product, API, pipeline, and contract tests
```

## License

Code and documentation in this repository are released under the MIT License. See `LICENSE`.
