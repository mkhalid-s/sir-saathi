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
- Ask users to confirm deadlines, eligibility, and final status on official portals before acting.
- Treat dates marked `reported` as provisional until confirmed by an official ECI/CEO source.
- Do not present guidance as legal advice.
- Do not expose full EPIC values, addresses, or raw roll records in guidance examples.
- If a deadline appears close or passed, tell the user to check official channels immediately.
