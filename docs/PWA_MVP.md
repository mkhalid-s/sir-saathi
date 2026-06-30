# PWA MVP

The first web app is a mobile-first Astro + Preact PWA.

## Included

- State selector backed by the canonical `config/states/*.json` registry.
- Safe state-specific "Find my name" entry flow that routes users through official search steps first, does not call indexed public search in the MVP fallback, lets users clear local hints, and hands not-found cases to missing-name guidance.
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
- WhatsApp-shareable checklist with official-confirmation and no-private-details reminder.
- Installable PWA manifest with app icon.
- Service worker for offline app-shell fallback; API calls are not cached.

## Not Included Yet

- Native mobile app.
- User accounts.
- Document uploads.
- National unscoped voter search.
- AI eligibility decisions.
- Full reviewed non-English UI translations beyond the first English UX pass.
