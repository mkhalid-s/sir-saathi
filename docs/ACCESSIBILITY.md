# Accessibility Standard And Release Review

SIR Saathi targets WCAG 2.2 Level AA for its public PWA. This target applies to the nationwide guidance experience, every state and union-territory page, translated interfaces, offline behavior, and any permission-gated indexed-search interface. The normative reference is the [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/).

The public `/accessibility/` help page is linked from the shared layout so it remains reachable from every route. It describes supported features and known limitations, makes no certification claim, links to the [GIGW help and accessibility guidance](https://guidelines.india.gov.in/help/), and separates accessibility feedback from official ECI voter assistance. No public feedback inbox is currently authorized: GitHub issue creation is restricted and the repository exposes only a non-deliverable noreply address. The page discloses that launch limitation instead of sending users to a broken or unofficial channel. Before public launch, an accountable owner must provide and rehearse a privacy-safe response channel. Reports must never contain voter names, EPICs, addresses, phone numbers, documents, private screenshots, voter records, or challenge tokens.

The dormant structured issue form and its activation/triage requirements are governed in `docs/ACCESSIBILITY_FEEDBACK.md`. Their presence in the repository is preparation only; the public page must remain unlinked while issue creation, accountable ownership, and response rehearsal are incomplete.

Passing automated checks is not a conformance claim. A public release needs both the repository gate and a recorded manual review of the deployed build.

## Automated Baseline

Build before running the audit:

```sh
npm run web:build
python scripts/check_accessibility.py
python scripts/check_visual_accessibility.py
```

The generated-page audit examines all HTML pages and fails on missing page language or direction, missing titles, invalid main/H1 structure, broken skip links, duplicate IDs, unresolved ARIA references, unlabelled form controls, and unsafe new-tab link relationships. The shared-style audit independently calculates WCAG relative-luminance ratios for 17 governed text, focus, and control-boundary pairs and verifies critical selectors still use those audited roles. The launch gate runs both after the production build. These deterministic checks do not evaluate raster content, browser rendering, typography, overlays, or every possible state and therefore do not replace the manual matrix.

## Manual Release Matrix

Use synthetic names and scopes only. Never put real EPIC numbers, addresses, phone numbers, documents, screenshots, or voter records into accessibility reports.

- Complete every guidance situation and the official-name-check fallback with keyboard only. Confirm visible focus is never obscured and the skip link works.
- Test current NVDA with Firefox or Chrome on Windows, VoiceOver with Safari on macOS or iOS, and TalkBack with Chrome on Android. Confirm field labels, disabled planned languages, guidance updates, errors, busy states, and result counts are announced meaningfully.
- Zoom text to 200% and the page to 400%; test 320 CSS-pixel reflow without two-dimensional scrolling except where content inherently requires it.
- Verify normal text contrast of at least 4.5:1, large text and meaningful non-text UI contrast of at least 3:1, visible focus, Windows forced-colours mode, and selected/disabled states.
- Apply WCAG text-spacing overrides and confirm content is not clipped or overlapped.
- Confirm interactive targets meet WCAG's 24-by-24 CSS-pixel minimum; SIR Saathi's primary control target is 44px.
- Enable reduced motion and confirm no interaction depends on animation.
- Test offline navigation and API failure behavior without trapping focus or announcing stale results.
- For every newly reviewed locale, verify document `lang`, translated pronunciation, line wrapping, placeholders, and share text with a fluent reviewer. For Urdu, additionally review right-to-left order, mixed-script names with `dir="auto"`, numbers, punctuation, focus order, and external URLs.
- Test at 200% browser text size in the smallest supported viewport for long state names and translated action labels.

## Release Evidence

Record the deployed commit, URL, browsers and assistive technologies with versions, reviewer identity, review date, failed checks, remediation links, and retest outcome. Do not record voter queries or personal data. A material navigation, form, translation, search-result, colour, or typography change requires a focused retest; a public-launch review requires the full matrix.

Create a fail-closed evidence template under an ignored local directory:

```sh
python -m pipeline.sir_saathi_pipeline.accessibility_evidence \
  --create-template \
  --output reports/accessibility/release.json
```

The template starts with no reviewer, no deployment identity, a false privacy attestation, and every check/environment marked `not_tested`. A human reviewer must record the deployed commit and real HTTPS origin; identity/date; every publishable locale; browser, OS, assistive-technology and version details; concise non-sensitive observations; failures, remediation references, and passing retests. Keep the detailed file in the access-controlled release evidence store and out of Git.

Validate it before launch:

```sh
python -m pipeline.sir_saathi_pipeline.accessibility_evidence \
  --validate reports/accessibility/release.json \
  --require-full-pass
```

The validator requires full-release scope, all 11 matrix checks, the desktop keyboard plus NVDA/Windows, VoiceOver/Apple, and TalkBack/Android environments, exact coverage of every currently publishable locale, a non-future review date, and an explicit no-personal-data attestation. A recorded failure is acceptable only after a remediation reference and passing retest. Its JSON output contains counts and stable blocker IDs only; it never repeats the deployed URL, reviewer, versions, or evidence notes. Validation establishes evidence completeness, not WCAG conformance by itself, and cannot replace the named human reviewer.
