# API And Database MVP

The first API surface is intentionally small:

- `GET /health`
- `GET /states`
- `POST /guidance`
- `POST /search`

Name search must be scoped by Assembly Constituency or polling-station part. API responses use redacted public records and do not expose full EPIC values, raw addresses, raw PDFs, or generated voter exports.

The initial PostgreSQL schema is in `db/schema.sql`; migration `db/migrations/0001_initial.sql` includes it for local database setup.
