-- Public search can read only exact roll/geography scopes explicitly enabled after review.
CREATE TABLE IF NOT EXISTS public_search_scopes (
    roll_version_id TEXT NOT NULL REFERENCES roll_versions(roll_version_id),
    ac_id TEXT NOT NULL REFERENCES assembly_constituencies(ac_id),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (roll_version_id, ac_id)
);
