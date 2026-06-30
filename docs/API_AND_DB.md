# API And Database MVP

The first API surface is intentionally small and served under the `/api` prefix:

- `GET /api/health`
- `GET /api/states`
- `GET /api/forms`
- `POST /api/guidance`
- `POST /api/search`

Name search fails closed unless the request is explicitly using the sanitized pilot fixture or a future state has passed public launch readiness. Public search must be scoped by Assembly Constituency; `part_number` can only narrow a search when `ac_number` is also present.

`GET /api/states` exposes canonical state metadata, including structured SIR schedule dates, CEO portal, official source labels, URLs, types, and `last_verified` dates so clients can show deadlines and source freshness.

`GET /api/forms` exposes the canonical SIR form catalogue and common document categories from `config/forms/sir-actions.json`.

The deployed `/api/search` handler also applies a fixed-window rate limit keyed by hashed client identity, state, and Assembly Constituency. This is intentionally small for the MVP and should move to a shared store before multi-process deployment.

API responses use redacted public records and do not expose full EPIC values, raw addresses, raw PDFs, or generated voter exports.

The initial PostgreSQL schema is in `db/schema.sql`; migration `db/migrations/0001_initial.sql` includes it for local database setup.

Parsed roll ingestion starts as a local-only staging mapper in `pipeline/sir_saathi_pipeline/ingestion.py`. It converts parser output into DB-shaped rows for `source_documents`, `roll_versions`, `extraction_runs`, and `voter_records`, validates parsed counts against source metadata, normalizes names for search, and stores EPIC only as a hash plus last four characters. It does not download PDFs, write raw exports, connect to Postgres, or enable public indexed search by itself.
