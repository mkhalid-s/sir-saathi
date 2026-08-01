# Multi-State Strategy

SIR Saathi covers all 28 states and 8 union territories in stages. Every jurisdiction starts with guidance and official links from the ECI CEO directory. Search is promoted only after source reliability, parser validation, privacy controls, and abuse prevention pass.

`config/jurisdictions.json` is the nationwide baseline. A jurisdiction without a reviewed override has `official_link_search` capability, an explicitly `unverified` schedule, no inferred deadlines, and no indexed voter data. Reviewed jurisdiction-specific schedules and capabilities live in `config/states/*.json` and replace the baseline entry.

## Capability Levels

- `guidance_only`: deadlines, forms, document checklists, official links, and offline fallback.
- `official_link_search`: deep links or instructions for official ECI/CEO search only.
- `pilot_indexed_search`: limited local pilot search for a validated area, redacted by default.
- `validated_indexed_search`: broader indexed search after parser, quality, privacy, and launch gates pass.

## Promotion Rules

A state can move from guidance to search only when:

1. Official sources and dates are recorded in a reviewed `config/states` override.
2. Schedule provenance is marked `official`; `reported` or `unverified` schedules cannot support public indexed search launch.
3. Source files are mapped by state, district, AC, part, year, language, and roll type.
4. Parser output is validated against official metadata counts.
5. Search is location-scoped and rate-limited.
6. Full EPIC values, addresses, raw PDFs, and parsed exports are not exposed or committed.
7. Public pages show source freshness and official verification fallback.

## Initial States

- Maharashtra is the first deep pilot because local parser work exists for 2002 Trombay rolls.
- West Bengal is the first contrast state because SIR material is already published and uses a different script/workflow shape.
