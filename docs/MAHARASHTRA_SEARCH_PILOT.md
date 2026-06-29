# Maharashtra Search Pilot

The Maharashtra search pilot proves the API contract with sanitized records only.

## Current Scope

- State: Maharashtra.
- Demo ACs: 172 and 173.
- Fixture: `tests/fixtures/mh_pilot_records.json`.
- Data: synthetic names, synthetic serials, and last-four-only EPIC hints.

## Rules

- Search must be scoped by Assembly Constituency.
- `part_number` is only a further narrowing field and must not be used without `ac_number`.
- Public indexed search fails closed unless a state passes launch readiness and abuse-prevention checks.
- The sanitized fixture path is available only when explicitly requested by tests/local demos.
- Results are redacted by default.
- No raw PDFs, parsed voter exports, full EPIC values, or addresses are committed.
- Real local data can be loaded only from ignored paths after parser validation and privacy review.
