# Privacy And Abuse Prevention

SIR Saathi treats electoral roll data as public but sensitive.

## Public Search Rules

- Search must be scoped by geography.
- No national browse endpoint.
- No bulk export endpoint.
- No raw PDF or parsed voter export in Git.
- No full EPIC value or raw address in public API responses.
- Public search requires abuse protection before launch.
- Logs must not store full EPICs, addresses, phone numbers, documents, or complete search strings.

## User Data Rules

The MVP does not require accounts, document uploads, or phone numbers. If future reminder features are added, they must be opt-in, purpose-limited, and deletable.

## AI Rules

AI may help explain source-backed guidance, translate copy, or summarize checklists. AI must not decide eligibility, invent deadlines, or process raw voter data by default.
