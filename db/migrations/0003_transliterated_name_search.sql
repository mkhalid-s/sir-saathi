-- Support scoped cross-script candidate lookup without changing public launch policy.
CREATE INDEX IF NOT EXISTS idx_voter_records_name_phonetic_trgm
    ON voter_records USING GIN (name_phonetic gin_trgm_ops);
