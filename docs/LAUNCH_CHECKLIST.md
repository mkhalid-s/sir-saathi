# Launch Checklist

Before any public launch:

- Sensitive-data scan passes.
- Python tests pass.
- Web build passes.
- PWA manifest, icon, and service worker registration are present.
- Service worker excludes `/api/*` from offline caching.
- npm audit reports no vulnerabilities for the web workspace.
- `python3 scripts/launch_gate.py` passes.
- API routes are served under `/api/*` and match reverse-proxy configuration.
- Privacy, methodology, and data-use pages are published.
- Search is scoped by Assembly Constituency and redacted.
- Public search fails closed unless state launch readiness and abuse-prevention checks pass.
- Public indexed search requires official schedule provenance, not reported-only dates.
- Public search has rate limiting and abuse protection; production multi-process deployments use a shared limiter store.
- Official links and source freshness are visible.
- Raw PDFs, parsed exports, local data, credentials, and generated reports are not committed.
- Commit message has no co-author trailer.
