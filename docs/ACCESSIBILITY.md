# Accessibility Standard And Release Review

SIR Saathi targets WCAG 2.2 Level AA for its public PWA. This target applies to the nationwide guidance experience, every state and union-territory page, translated interfaces, offline behavior, and any permission-gated indexed-search interface. The normative reference is the [W3C Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/).

Passing automated checks is not a conformance claim. A public release needs both the repository gate and a recorded manual review of the deployed build.

## Automated Baseline

Build before running the audit:

```sh
npm run web:build
python scripts/check_accessibility.py
```

The audit examines all generated HTML pages and fails on missing page language or direction, missing titles, invalid main/H1 structure, broken skip links, duplicate IDs, unresolved ARIA references, unlabelled form controls, and unsafe new-tab link relationships. The launch gate runs it after the production build.

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
