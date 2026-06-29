# AI Product Team Operating Model

SIR Saathi is built in small autonomous slices. Each slice has a clear outcome, tests, review, commit, and push.

## Roles

- Orchestrator: chooses the slice and owns the final gate.
- Product agent: checks the user journey and acceptance criteria.
- Research agent: checks official dates, source links, and civic-process assumptions.
- Frontend agent: owns mobile PWA UX.
- Backend agent: owns API contracts, redaction, and validation.
- Data agent: owns ingestion, parser adapters, and quality reports.
- QA agent: owns tests and smoke checks.
- Security/privacy agent: blocks secrets, raw data, unsafe logging, and public search risks.
- Reviewer agent: reviews the diff before commit.

## Slice Gate

Before a slice is committed or pushed, run:

```sh
python scripts/slice_gate.py
```

The gate runs the sensitive-data scan, Python tests, web audit, web build, launch gate, and last-commit trailer check.

## Commit Policy

- Commit one validated slice at a time.
- Use concise messages focused on the purpose of the change.
- Do not add co-author trailers.
- Push to the personal repository only after validation passes.
- Do not commit raw voter data, generated exports, credentials, local configs, or screenshots containing real records.

## Completed Initial Loop

The initial autonomous loop established foundation safety, state registry, deterministic guidance, importable pipeline modules, API/database contracts, PWA MVP, sanitized Maharashtra search pilot, privacy safeguards, and deployment runbooks.
