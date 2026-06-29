# API And Database MVP

The first API surface is intentionally small and served under the `/api` prefix:

- `GET /api/health`
- `GET /api/states`
- `GET /api/forms`
- `POST /api/guidance`
- `POST /api/search`

Name search fails closed unless the request is explicitly using the sanitized pilot fixture or a future state has passed public launch readiness. Public search must be scoped by Assembly Constituency; `part_number` can only narrow a search when `ac_number` is also present.

`GET /api/states` exposes canonical state metadata, including official source labels, URLs, types, and `last_verified` dates so clients can show source freshness.

`GET /api/forms` exposes the canonical SIR form catalogue and common document categories from `config/forms/sir-actions.json`.

The deployed `/api/search` handler also applies a fixed-window rate limit keyed by hashed client identity, state, and Assembly Constituency. This is intentionally small for the MVP and should move to a shared store before multi-process deployment.

API responses use redacted public records and do not expose full EPIC values, raw addresses, raw PDFs, or generated voter exports.

The initial PostgreSQL schema is in `db/schema.sql`; migration `db/migrations/0001_initial.sql` includes it for local database setup.
