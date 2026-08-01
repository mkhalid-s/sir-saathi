# PWA MVP

The first web app is a mobile-first Astro + Preact PWA.

## Included

- State selector and 36 shareable state/UT pages backed by `config/jurisdictions.json` plus reviewed `config/states/*.json` overrides.
- Safe state-specific "Find my name" entry flow that routes users through official search steps first, lets users clear local hints, and hands not-found cases to missing-name guidance.
- A dormant-by-default indexed-search client that renders only for a jurisdiction marked launch-ready. It requires AC scope, explicitly renders Turnstile with the `voter_search` action, submits only after the user's search action, resets the single-use response, and displays only bounded redacted API fields.
- Situation selector covering verification, missing name, new voter, shifted address, correction, deceased-family entry, duplicate entry, and portal failure.
- Follow-up SIR questions for BLO visit, enumeration form receipt/submission, current roll match, and base/base-roll match.
- SIR deadline card.
- Next-action checklist.
- Guidance boundary note that SIR Saathi does not decide eligibility or replace official channels.
- Document checklist backed by `config/forms/sir-actions.json`.
- Source-backed forms and common documents reference.
- State-by-state search availability status that stays privacy-safe and explains official schedule-provenance requirements.
- Official portal link.
- Source labels, source freshness, and launch-readiness warning.
- UI language selector that shows English as available and non-English translations as planned until human review.
- Canonical locale governance in `config/locales.json`; every language tracked by the nationwide catalogue must have an explicit availability and review state.
- Canonical English message keys in `config/translations/en.json` and a fail-closed readiness report. A non-English locale can be marked available only when it has the exact key set, preserves named placeholders, and records a fluent human reviewer and review date.

Run `python -m pipeline.sir_saathi_pipeline.translation_catalog --fail-on-invalid-available` in review and deployment workflows. Missing planned catalogues are reported as pending, while any locale marked available without a complete reviewed catalogue fails the command.

The hydrated wizard loads catalogues through `apps/web/src/lib/i18n.ts`; catalogue discovery is automatic at build time, but only locales marked `available` in the governed registry can render. Safety text, all form controls, official and indexed-search instructions, every situation-specific guidance title/summary/action/document, status, deadline, provenance, and checklist sharing use keyed messages with checked placeholders. Draft or missing catalogues cannot be selected and fall back to the reviewed English source copy.

- WhatsApp-shareable checklist with official-confirmation and no-private-details reminder.
- Installable PWA manifest with app icon.
- Service worker for offline app-shell fallback; API calls are not cached.
- Keyboard skip navigation, visible focus indicators, semantic main landmarks, and status announcements for interactive results.

## Not Included Yet

- Native mobile app.
- User accounts.
- Document uploads.
- National unscoped voter search.
- AI eligibility decisions.
- Full reviewed non-English UI translations beyond the first English UX pass.
