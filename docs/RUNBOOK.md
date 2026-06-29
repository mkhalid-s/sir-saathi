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

- Weekly source-date review for active SIR states.
- Weekly dependency audit.
- Daily API/PWA health checks after launch.
- Backup restore test before enabling real indexed search.
