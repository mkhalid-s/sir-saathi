# Guidance Rules

The first version of SIR Saathi guidance is deterministic. It does not use an LLM to decide voter eligibility or legal outcomes.

## Inputs

- State ID from `config/states`.
- User situation such as existing voter, missing name, shifted address, correction, new voter, duplicate entry, deceased family member, or portal failure.
- Optional status flags for BLO visit, enumeration form receipt/submission, current roll match, and base roll match.

## Outputs

- Priority.
- Plain-language summary.
- Next actions.
- Document checklist.
- Official links.
- Deadline from the state registry.
- Source labels and warnings.
- Last-checked source dates, not a guarantee that source content has not changed.
- Schedule provenance, distinguishing official-source-backed dates from reported dates.

## Safety Rules

- Always route final submission/status to official ECI, CEO, BLO, or ERO channels.
- Show guidance as next-action support, not as a voter eligibility decision.
- Ask users to confirm deadlines, eligibility, and final status on official portals before acting.
- Treat dates marked `reported` as provisional until confirmed by an official ECI/CEO source.
- Do not present guidance as legal advice.
- Do not expose full EPIC values, addresses, or raw roll records in guidance examples.
- If a deadline appears close or passed, tell the user to check official channels immediately.
- Treat both unverified and officially pending schedules as unavailable: hide and ignore BLO, enumeration-form, and base-roll answers, show no inferred SIR deadline, and direct the voter to current rolls and official notices. Clear state-specific status answers whenever the jurisdiction changes.
- Ask status questions only when they affect the selected situation and revision phase. Clear prior status answers when the situation changes. Enumeration answers may change guidance only before or during enumeration; completed revisions must use final/current-roll remedies and must never send a voter back to enumeration.
- Keep PWA and API urgency aligned: a missing current-roll entry is urgent, a received-but-unsubmitted enumeration form is high priority only while enumeration is actionable, and passed or imminent deadlines use explicit warning copy rather than future-tense instructions.
