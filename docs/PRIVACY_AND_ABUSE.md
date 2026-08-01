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
- Before calling the external challenge verifier, the API applies a fixed-window verification-attempt limit per hashed client. A separate public-search limit uses the same client-global scope across all states and ACs, so invalid-token floods and search-scope rotation cannot reset their respective burst allowances.
- Logs must not store full EPICs, addresses, phone numbers, documents, or complete search strings.
- Public-search application logs contain only stable event IDs for completion, rejection, rate limiting, dependency loss, or backend failure. They omit request bodies, query fragments, client identities, challenge tokens, result counts, exception details, and voter records.
- Caddy and the API independently cap body-bearing API requests at 16 KiB. The application verifies streamed bytes rather than trusting `Content-Length`, and rejects oversized input before JSON parsing, external verification, logging, or database work.
- Each public PostgreSQL search runs in an explicitly read-only transaction with a three-second statement timeout. Connections close on success or failure, and database exception details never enter the public response or application event log.
- Shared checklists must not include EPIC, address, phone, document, or other private voter details.
- Scope-authorization reasons and readiness snapshots must contain no voter names, EPIC values, addresses, or search strings.

## Abuse Protection MVP

Local sanitized demonstrations use an in-process fixed-window limiter. Real indexed search requires the shared Redis limiter configured by `SIR_SAATHI_REDIS_URL`; without it, the API fails closed before querying voter records. The shared check uses one atomic Lua operation to increment the scoped counter and set its expiry, so all API workers enforce the same window. Bucket keys hash the client identity before combining it with state and Assembly Constituency scope, so raw client identifiers are not stored in limiter keys. Redis errors return temporary unavailability rather than bypassing the limit.

Forwarding headers are ignored by default. When the API is reachable only through a known proxy chain, set `SIR_SAATHI_TRUSTED_PROXY_HOPS` to the exact number of trusted hops (for example, `1` for one local Caddy proxy). The API walks `X-Forwarded-For` from the right, validates the selected value as an IP address, and uses it only as ephemeral input to Turnstile and the hashed rate-limit identity. Do not enable this setting while clients can reach the API directly.

Real indexed search also requires server-side Cloudflare Turnstile verification. Clients submit only an opaque `turnstile_response`; the API posts it to Cloudflare using `SIR_SAATHI_TURNSTILE_SECRET`, checks the expected `voter_search` action and optional `SIR_SAATHI_TURNSTILE_HOSTNAME`, and fails closed on missing configuration, timeout, malformed response, hostname mismatch, or action mismatch. A client-supplied “verified” boolean is rejected. The sanitized synthetic pilot does not expose voter data and remains available without Turnstile for development demonstrations.

## User Data Rules

The MVP does not require accounts, document uploads, or phone numbers. If future reminder features are added, they must be opt-in, purpose-limited, and deletable.

Guidance-only and official-link fallback flows must not ask users to enter names, addresses, districts, constituencies, or part numbers. Name and exact AC/optional part inputs may render only for an explicitly launch-ready indexed-search jurisdiction, and the interface must explain that those scoped values leave the device only when the user submits the protected search action.

## Cross-Year Matching Rules

- Matching runs locally and remains scoped to one state and Assembly Constituency.
- Scores create review candidates only; they never establish identity, registration status, or eligibility.
- Confirmation and rejection require reviewer identity and timestamp.
- Safe reports contain aggregate score bands and ambiguity counts, not names or record identifiers.
- Public APIs do not expose match-candidate tables or bulk relationship graphs.

## AI Rules

AI may help explain source-backed guidance, translate copy, or summarize checklists. AI must not decide eligibility, invent deadlines, or process raw voter data by default.
