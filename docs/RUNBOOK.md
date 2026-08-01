# Operator Runbook

## Before Public Launch

- Run `python scripts/launch_gate.py`.
- Run `npm audit --workspace apps/web`.
- Confirm no raw data is tracked with `git status --ignored`.
- Confirm search remains scoped and redacted.

## Incident Response

If sensitive data is exposed:

1. Disable the public route or search feature.
2. Preserve logs needed to understand scope, but do not copy sensitive records into tickets.
3. Remove the exposed artifact.
4. Rotate any exposed credentials if relevant.
5. Publish a short incident note when users may be affected.

## Routine Checks

- Run `python -m pipeline.sir_saathi_pipeline.source_freshness --fail-on-stale` before deployment and at least daily while an SIR schedule is active. Active schedule sources expire after 7 days; completed or unverified baseline sources expire after 90 days.
- Review sources marked `expiring` before they become launch blockers. The report contains public source labels and dates only—never voter queries or records.
- Weekly dependency audit.
- Daily API/PWA health checks after launch.
- Backup restore test before enabling real indexed search.
