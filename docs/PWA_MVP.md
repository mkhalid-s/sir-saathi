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
- Shared, source-governed Phase III dates for all 19 jurisdictions named in the official ECI schedule; remaining schedules fail closed as unverified until reviewed evidence is added.
- Official final-publication evidence for completed Phase II jurisdictions is recorded independently, so later extensions do not get overwritten by the original common target date.
- UI language selector that shows English as available and non-English translations as planned until human review.
- Canonical locale governance in `config/locales.json`; every language tracked by the nationwide catalogue must have an explicit availability and review state.
- Every reviewed UI language is selectable in every jurisdiction, independent of that jurisdiction's official-language list. Planned state-relevant languages remain visible but disabled. Reviewed choices persist locally and can be shared with the fail-closed `?lang=` URL parameter; unknown, missing, and planned catalogues resolve to English.
- Homepage hero, nationwide search directory, forms reference, safety messaging, and guidance controls now read from the same reviewed catalogue. Locale-prefixed home routes are generated only for catalogues that pass registry activation; planned or draft catalogues cannot create public pages.
- Locale-prefixed routes cover the homepage, every state/UT guide, privacy, methodology, and data-use pages. Internal guide, policy, and jurisdiction navigation preserves the locale; selecting another reviewed language reloads the complete localized page rather than translating only the interactive island.
- Network-first offline caching preserves a previously visited locale route and falls back to that locale's cached homepage before using the English app shell. API responses remain excluded from every cache.
- Schedule and source-check dates use locale-aware India-time formatting. Official source labels and jurisdiction-specific provenance notes remain verbatim evidence rather than being silently machine-translated.
- Catalogue readiness is enforced twice: the Python review gate validates files before activation, and the web build independently rechecks schema version, exact keys, placeholders, reviewer identity, review date, and registry state before creating any localized route.
- All 36 jurisdiction display names are governed translation keys while canonical `IN-*` IDs and official links remain unchanged. When more than one reviewed locale exists, every public page shows a keyboard-accessible language switcher that preserves the current home, policy, or jurisdiction route.
- Canonical English message keys in `config/translations/en.json` and a fail-closed readiness report. A non-English locale can be marked available only when it has the exact key set, preserves named placeholders, and records a fluent human reviewer and review date.
- Locale direction is governed alongside availability. The hydrated wizard updates the document `lang` and `dir` attributes for reviewed selections, including right-to-left rendering for Urdu.

Run `python -m pipeline.sir_saathi_pipeline.translation_catalog --fail-on-invalid-available` in review and deployment workflows. Missing planned catalogues are reported as pending, while any locale marked available without a complete reviewed catalogue fails the command.

Start a human translation review without placing draft copy in the runtime catalogue:

```sh
python -m pipeline.sir_saathi_pipeline.translation_catalog \
  --create-review-packet mr \
  --output data/translation-review/mr.json
```

The packet records every English source string, required placeholder, and a digest of the complete source catalogue. A fluent reviewer fills `translation`, changes the packet review status to `reviewed`, and records `reviewed_by` plus an ISO `reviewed_at` date. Compile it only after that review:

```sh
python -m pipeline.sir_saathi_pipeline.translation_catalog \
  --compile-reviewed-packet data/translation-review/mr.json \
  --output config/translations/mr.json
```

Compilation rejects incomplete strings, changed keys or source copy, lost placeholders, missing reviewer accountability, and stale source digests. It does not activate the locale: `config/locales.json` must still be changed from `planned` to `available` in a reviewed code change. This keeps draft or stale translations fail-closed.

The hydrated wizard loads catalogues through `apps/web/src/lib/i18n.ts`; catalogue discovery is automatic at build time, but only locales marked `available` in the governed registry can render. Safety text, all form controls, official and indexed-search instructions, every situation-specific guidance title/summary/action/document, status, deadline, provenance, and checklist sharing use keyed messages with checked placeholders. Draft or missing catalogues cannot be selected and fall back to the reviewed English source copy.

- WhatsApp-shareable checklist with official-confirmation and no-private-details reminder.
- Installable PWA manifest with app icon.
- Service worker for offline app-shell fallback; API calls are not cached.
- Keyboard skip navigation, visible focus indicators, semantic main landmarks, and status announcements for interactive results.
- Assistive-technology announcements when guidance changes, labelled language-readiness help, automatic direction for voter names, 44px interactive targets, reduced-motion safeguards, and forced-colour focus visibility.
- A generated-site structural audit covering all 40 pages. It verifies language and direction metadata, titles, main and heading landmarks, skip targets, unique IDs, ARIA references, form-control labels, and safe new-tab links. This deterministic check complements rather than replaces manual screen-reader, zoom, reflow, and contrast review.

## Not Included Yet

- Native mobile app.
- User accounts.
- Document uploads.
- National unscoped voter search.
- AI eligibility decisions.
- Full reviewed non-English UI translations beyond the first English UX pass.
