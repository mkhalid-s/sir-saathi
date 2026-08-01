-- Store explainable cross-year proposals; confirmation/rejection requires review metadata.
CREATE TABLE IF NOT EXISTS voter_record_match_candidates (
    match_candidate_id TEXT PRIMARY KEY,
    base_voter_record_id TEXT NOT NULL REFERENCES voter_records(voter_record_id),
    current_voter_record_id TEXT NOT NULL REFERENCES voter_records(voter_record_id),
    score NUMERIC(5,4) NOT NULL CHECK (score >= 0 AND score <= 1),
    feature_scores JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'confirmed', 'rejected')),
    method_version TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (base_voter_record_id, current_voter_record_id, method_version),
    CHECK (status = 'proposed' OR (reviewed_at IS NOT NULL AND reviewed_by IS NOT NULL))
);
