# Implementation Status And Direction

Reviewed on 2026-08-01. This is the handoff map for the autonomous review → validate → implement → verify loop. “Implemented” means present in the repository and covered by a gate; it does not mean that external human review or a production launch has happened.

## Implemented

| Area | Current evidence |
|---|---|
| Nationwide guidance | All 36 states and union territories have governed IDs, display names, CEO links, schedule provenance, source-freshness metadata, and a generated public guide. The find-name fallback separately labels the canonical ECI voter-services destination and the selected state/UT CEO portal. The English build has 40 indexable guidance/policy pages plus an accessible no-index 404 recovery page. |
| SIR schedules | Reviewed official evidence drives current phases and deadlines. Himachal Pradesh, Jammu and Kashmir, and Ladakh remain explicitly “schedule to be announced”; the app invents no dates. |
| Guidance and forms | Situation-based, date-aware guidance, privacy-safe printable checklists, complete governed state timelines, and the canonical enumeration/Form 6/Form 7/Form 8 reference with official portal actions are shared by the PWA and API. Printed checklists omit entered name/location fields; missing schedule dates remain omitted rather than inferred. Guidance is advisory and always points back to official channels. |
| Privacy-safe search boundary | Public indexed search is disabled for every jurisdiction by default, so the nationwide fallback asks for no voter name or location fields. Name and exact AC/optional part inputs render only inside an explicitly launch-ready boundary. Any future scope requires an exact roll version and versioned AC, official schedule provenance, a readiness report, independent human authorization, server-side Turnstile, shared Redis rate limiting, redacted results, and an append-only decision event. |
| Local data workflow | Reviewed-source manifests, checksum verification, dry-run ingestion, idempotent loading, scoped local search, aggregate readiness reports, cross-year candidate review, and dry-run-first public-scope authorization exist. Raw rolls and generated voter data remain local and ignored. |
| Languages | Seventeen locale codes and text directions are governed. English is the only publishable catalogue, with 331 source messages. Runtime routes, API fallback metadata, locale-preserving links, RTL support, source-pinned risk-labelled review packets, exact-key/placeholder validation, and distinct translator/reviewer attestations are implemented for future locales. |
| Accessibility | The generated-page structural audit covers every public page and currently reports zero findings. Keyboard, live-region, RTL, forced-colour, reduced-motion, reflow, zoom, and assistive-technology expectations are documented; manual conformance evidence is still required. |
| PWA and offline | Install metadata, interoperable icons, service-worker update controls, a localized offline notice, and a build-generated precache of every jurisdiction/policy page plus hashed UI assets are present. API responses are never cached. |
| Deployment and security | Caddy serves the PWA and `/api/*` on one HTTPS origin. The template includes HSTS, anti-framing, no-sniff, referrer, permissions, cross-origin-resource, and deny-by-default Turnstile-compatible CSP headers. Production dependencies are locked, and a value-redacting preflight separately checks guidance-only and indexed-search configuration shapes. |
| Operations | Separate liveness and deployment-mode-aware readiness preserve guidance availability while failing indexed search closed on dependency loss; a value-redacting 32-contract deployed-origin audit covers the HTTP surface. A daily official-source freshness workflow, source expiry gates, canonical/alternate/sitemap/robots validation, checksum-pinned serialized database migrations, direct-to-`age` encrypted backups with non-destructive archive verification, sensitive-data scanning, dependency audit, tests, build, accessibility audit, and discoverability audit are part of the release gate. |

The review snapshot passes 258 tests, reports zero npm vulnerabilities, verifies 140 governed source records as fresh, precaches 55 generated offline assets, and reports zero automated accessibility or discoverability findings across 40 indexable English pages plus the no-index error page.

## Pending External Evidence

These items must not be fabricated or auto-approved:

1. Fluent human translation and legal/civic review for Assamese, Bengali, Gujarati, Hindi, Kannada, Konkani, Mizo, Malayalam, Meitei, Marathi, Nepali, Odia, Punjabi, Tamil, Telugu, and Urdu. A locale becomes public only after its complete catalogue and attestation pass the existing gate.
2. Authorized official roll samples and record-accounting evidence for each parser/layout. Only the reviewed Maharashtra 2002 historical/base-roll parser is ingestion-ready; the current Maharashtra Unicode parser remains synthetic-fixture-only.
3. Per-scope data-quality review and independent human authorization before enabling any real public indexed-search scope. Repository defaults must remain off.
4. Manual accessibility review on the deployed build using the matrix in `docs/ACCESSIBILITY.md`.
5. Production infrastructure evidence: real HTTPS origin, Turnstile hostname/key pair, protected Redis/PostgreSQL, trusted proxy count, encrypted backup and restore drill, live migration apply/check, uptime alert owner, and rollback rehearsal.
6. Ongoing editorial verification when official source records approach their 7-day active or 90-day inactive freshness limit.

## Direction

Work should proceed in this order:

1. **Production rehearsal without voter data.** Build with the final origin and Turnstile test keys, run migrations against an ephemeral PostgreSQL 16 database, exercise Caddy/TLS/CSP, test offline installation, restore a backup into an isolated database, and record the manual accessibility matrix.
2. **Human-reviewed language wave.** Start with Hindi plus the language of the first operational state. Use generated translation packets, two-person review for safety-critical guidance, native-script/RTL device testing, and only then switch the locale registry to `available`.
3. **One real roll onboarding pilot.** Obtain authorized official material, draft and review its source manifest, validate checksum and parser accounting, dry-run/load locally, inspect aggregate quality, and keep public search disabled.
4. **One exact public-search scope rehearsal.** Use a non-production or sanitized environment to exercise enable, query, rate-limit, Turnstile, audit event, and immediate disable. Real voter data still requires explicit accountable approval outside automation.
5. **Repeat state by state.** Add parser fixtures and source evidence per layout, never by assuming one state’s PDF format applies nationally. The nationwide guidance layer can remain useful while indexed data coverage expands independently.

## Autonomous Stop Conditions

The agent should continue improving reversible code, tests, documentation, and safe operational tooling. It must stop rather than infer approval when a step needs raw electoral-roll access, production credentials, a public-domain decision, human translation attestation, accessibility sign-off, or authorization to expose a real indexed-search scope.
