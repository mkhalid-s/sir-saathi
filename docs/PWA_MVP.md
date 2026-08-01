# PWA MVP

The first web app is a mobile-first Astro + Preact PWA.

## Included

- State selector and 36 shareable state/UT pages backed by `config/jurisdictions.json` plus reviewed `config/states/*.json` overrides.
- Safe state-specific "Find my name" entry flow that routes users through official search steps first, clearly separates the canonical ECI voter-services destination from each state or UT CEO portal, lets authorized-scope users clear local hints, and hands not-found cases to missing-name guidance.
- A dormant-by-default indexed-search client that renders only for a jurisdiction marked launch-ready. It requires AC scope, explicitly renders Turnstile with the `voter_search` action, submits only after the user's search action, resets the single-use response, and displays only bounded redacted API fields.
- Situation selector covering verification, missing name, new voter, shifted address, correction, deceased-family entry, duplicate entry, and portal failure.
- Follow-up SIR questions for BLO visit, enumeration form receipt/submission, current roll match, and base/base-roll match.
- SIR deadline card.
- Next-action checklist.
- Guidance boundary note that SIR Saathi does not decide eligibility or replace official channels.
- Document checklist backed by `config/forms/sir-actions.json`, with a device-neutral print/save view that excludes entered name and location fields.
- Source-backed forms and common documents reference.
- A source-governed official-assistance panel on the homepage and every state/UT guide links to ECI complaint, application-tracking, BLO callback, 1950, email, the relevant CEO portal, and ECI's CEO contact-directory fallback without collecting a complaint or voter document.
- State-by-state search availability status that stays privacy-safe and explains official schedule-provenance requirements.
- A progressively enhanced keyboard-labelled directory filter searches localized jurisdiction names and canonical `IN-*` codes, announces the visible count, and leaves all 36 guide rows in the static no-JavaScript page.
- Separate governed links for each jurisdiction's CEO portal and its schedule evidence, so an action button never labels a PDF or evidence subpage as the CEO homepage.
- Source labels, source freshness, and launch-readiness warning.
- Shared, source-governed Phase III dates for all 19 jurisdictions named in the official ECI schedule; remaining schedules fail closed as unverified until reviewed evidence is added.
- Official final-publication evidence for completed Phase II jurisdictions is recorded independently, so later extensions do not get overwritten by the original common target date.
- UI language selector that shows English as available and non-English translations as planned until human review.
- A public, localized language-availability page enumerates all 24 governed codes and directions—all 22 Eighth Schedule languages plus English and Mizo—distinguishes publishable, planned, and blocked activation states, and explains the independent human-review boundary without exposing draft copy or reviewer identities. The API exposes the same safe readiness facts and official coverage source.
- Canonical locale governance in `config/locales.json`; every language tracked by the nationwide catalogue must have an explicit availability and review state.
- Every reviewed UI language is selectable in every jurisdiction, independent of that jurisdiction's official-language list. Planned state-relevant languages remain visible but disabled. Reviewed choices persist locally and can be shared with the fail-closed `?lang=` URL parameter; unknown, missing, and planned catalogues resolve to English.
- Homepage hero, nationwide search directory, forms reference, safety messaging, and guidance controls now read from the same reviewed catalogue. Locale-prefixed home routes are generated only for catalogues that pass registry activation; planned or draft catalogues cannot create public pages.
- Locale-prefixed routes cover the homepage, every state/UT guide, privacy, methodology, data-use, and language-availability pages. Internal guide, policy, and jurisdiction navigation preserves the locale; selecting another reviewed language reloads the complete localized page rather than translating only the interactive island.
- Network-first offline caching precaches every generated jurisdiction/policy page and its hashed UI assets, preserves a previously visited locale route, and falls back to that locale's homepage before using the English app shell. API responses remain excluded from every cache, and a post-build check prevents incomplete precache manifests.
- Every route displays a localized live-region notice when the browser reports it is offline, explicitly separating cached guidance from official links and indexed search that still require connectivity.
- Unknown routes retain a real 404 status while rendering an accessible, no-index recovery page with direct links to the homepage and nationwide jurisdiction directory.
- Schedule and source-check dates use locale-aware India-time formatting. Official source labels and jurisdiction-specific provenance notes remain verbatim evidence rather than being silently machine-translated.
- Catalogue readiness is enforced twice: the Python review gate validates files before activation, and the web build independently rechecks schema version, exact keys, placeholders, reviewer identity, review date, and registry state before creating any localized route.
- All 36 jurisdiction display names are governed translation keys while canonical `IN-*` IDs and official links remain unchanged. When more than one reviewed locale exists, every public page shows a keyboard-accessible language switcher that preserves the current home, policy, or jurisdiction route.
- Every generated guidance page has one absolute canonical URL plus reviewed-locale and `x-default` alternates. The sitemap and robots policy are generated from the same 36-jurisdiction and runtime-ready locale catalogues, then checked against the built HTML.
- Canonical English message keys in `config/translations/en.json` and a fail-closed readiness report. A non-English locale can be marked available only when it has the exact key set, preserves named placeholders, and records a fluent human reviewer and review date.
- Locale direction is governed alongside availability. The hydrated wizard updates the document `lang` and `dir` attributes for reviewed selections, including right-to-left rendering for Urdu.

Run `python -m pipeline.sir_saathi_pipeline.translation_catalog --fail-on-invalid-available` in review and deployment workflows. Missing planned catalogues are reported as pending, while any locale marked available without a complete reviewed catalogue fails the command.

Create a new private campaign bundle for every planned language in one atomic operation:

```sh
python -m pipeline.sir_saathi_pipeline.translation_campaign \
  --create data/translation-campaign/source-2026-08-01
python -m pipeline.sir_saathi_pipeline.translation_campaign \
  --check data/translation-campaign/source-2026-08-01
```

The bundle contains one source-pinned review packet per planned locale plus a manifest with counts, directions, and safety-critical workload. Creation refuses to overwrite any existing directory, keeping human work recoverable. The redacted check permits in-progress translations and private review identities but rejects changed English source text, missing locales, altered source/risk/placeholder metadata, or stale manifests. It never translates, approves, compiles, or activates a locale. Repository bundles are allowed only under ignored `data/`, `reports/`, or `samples/` directories.

Start a human translation review without placing draft copy in the runtime catalogue:

```sh
python -m pipeline.sir_saathi_pipeline.translation_catalog \
  --create-review-packet mr \
  --output data/translation-review/mr.json
```

The schema-v2 packet records locale direction, every English source string, its section, required placeholders, a deterministic `safety_critical` or `standard` risk label, the number of critical entries, and a digest of the complete source catalogue. A fluent translator fills `translation` and records `translated_by`. A different fluent reviewer checks the complete catalogue—with extra care for safety-critical guidance—then changes the packet status to `reviewed` and records `reviewed_by` plus an ISO `reviewed_at` date. Compile it only after that independent review:

```sh
python -m pipeline.sir_saathi_pipeline.translation_catalog \
  --compile-reviewed-packet data/translation-review/mr.json \
  --output config/translations/mr.json
```

Compilation rejects incomplete strings, changed keys or source copy, tampered risk/section/placeholder metadata, lost placeholders, missing identities, the same person acting as translator and reviewer, direction drift, changed review requirements, and stale source digests. The compiled runtime catalogue retains both accountable identities. Compilation does not activate the locale: `config/locales.json` must still be changed from `planned` to `available` in a reviewed code change. This keeps draft, singly reviewed, or stale translations fail-closed.

After every translation is filled—but before marking the packet reviewed—generate a local in-context review sheet:

```sh
python -m pipeline.sir_saathi_pipeline.translation_catalog \
  --render-review-preview data/translation-review/mr.json \
  --output data/translation-preview/mr.html
```

The self-contained HTML groups strings by UI section, highlights safety-critical entries, shows the current English source beside translated copy, and applies the locale's governed text direction. It has no network dependencies, escapes translated markup, carries a restrictive CSP and `noindex`, and prominently says it is not reviewed or publishable. In-repository preview output is allowed only under ignored `data/`, `reports/`, or `samples/` paths and is rejected from runtime catalogue, public asset, and build-output directories. Preview generation validates completeness, the current source digest, exact keys, risk metadata, and placeholders, but cannot satisfy or bypass independent human review.

The hydrated wizard loads catalogues through `apps/web/src/lib/i18n.ts`; catalogue discovery is automatic at build time, but only locales marked `available` in the governed registry can render. Safety text, all form controls, official and indexed-search instructions, every situation-specific guidance title/summary/action/document, status, deadline, provenance, and checklist sharing use keyed messages with checked placeholders. Draft or missing catalogues cannot be selected and fall back to the reviewed English source copy.

- WhatsApp-shareable checklist with official-confirmation and no-private-details reminder.
- Installable PWA manifest with reproducible 192px/512px PNG, scalable SVG, dedicated maskable, and Apple touch icon variants derived from one reviewed SVG source.
- Service worker for offline app-shell fallback; API calls are not cached.
- Keyboard skip navigation, visible focus indicators, semantic main landmarks, and status announcements for interactive results.
- Assistive-technology announcements when guidance changes, labelled language-readiness help, automatic direction for voter names, 44px interactive targets, reduced-motion safeguards, and forced-colour focus visibility.
- A generated-site structural audit covering all 42 HTML pages, including the error page. It verifies language and direction metadata, titles, main and heading landmarks, skip targets, unique IDs, ARIA references, form-control labels, and safe new-tab links. This deterministic check complements rather than replaces manual screen-reader, zoom, reflow, and contrast review.
- An executable browser-guidance matrix bundles the production TypeScript and checks all 36 jurisdictions across all eight situations, phase-aware deadlines, completed and unavailable schedules, and adversarial stale-answer combinations.

## Not Included Yet

- Native mobile app.
- User accounts.
- Document uploads.
- National unscoped voter search.
- AI eligibility decisions.
- Full reviewed non-English UI translations beyond the first English UX pass.
