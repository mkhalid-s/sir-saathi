# Privacy And Abuse Prevention

SIR Saathi treats electoral roll data as public but sensitive.

## Public Search Rules

- Search must be scoped by geography.
- No national browse endpoint.
- No bulk export endpoint.
- No raw PDF or parsed voter export in Git.
- No full EPIC value or raw address in public API responses.
- Public search requires abuse protection before launch.
- Public indexed search requires official schedule provenance before launch.
- The API search route applies a fixed-window rate limit per hashed client/state/AC bucket.
- Logs must not store full EPICs, addresses, phone numbers, documents, or complete search strings.
- Shared checklists must not include EPIC, address, phone, document, or other private voter details.

## Abuse Protection MVP

The first implementation uses an in-process fixed-window limiter. Bucket keys hash the client identity before combining it with state and Assembly Constituency scope, so raw client identifiers are not stored in limiter keys. A production deployment should replace this with a shared store such as Redis before running multiple API processes.

Real indexed search also requires server-side Cloudflare Turnstile verification. Clients submit only an opaque `turnstile_response`; the API posts it to Cloudflare using `SIR_SAATHI_TURNSTILE_SECRET`, checks the expected `voter_search` action and optional `SIR_SAATHI_TURNSTILE_HOSTNAME`, and fails closed on missing configuration, timeout, malformed response, hostname mismatch, or action mismatch. A client-supplied “verified” boolean is rejected. The sanitized synthetic pilot does not expose voter data and remains available without Turnstile for development demonstrations.

## User Data Rules

The MVP does not require accounts, document uploads, or phone numbers. If future reminder features are added, they must be opt-in, purpose-limited, and deletable.

## Cross-Year Matching Rules

- Matching runs locally and remains scoped to one state and Assembly Constituency.
- Scores create review candidates only; they never establish identity, registration status, or eligibility.
- Confirmation and rejection require reviewer identity and timestamp.
- Safe reports contain aggregate score bands and ambiguity counts, not names or record identifiers.
- Public APIs do not expose match-candidate tables or bulk relationship graphs.

## AI Rules

AI may help explain source-backed guidance, translate copy, or summarize checklists. AI must not decide eligibility, invent deadlines, or process raw voter data by default.
