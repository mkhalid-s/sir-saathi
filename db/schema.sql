-- SIR Saathi initial relational schema.
-- Raw PDFs and generated voter exports stay outside Git and are loaded locally.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS states (
    state_id TEXT PRIMARY KEY,
    eci_state_code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    default_language TEXT NOT NULL,
    data_capability TEXT NOT NULL,
    public_launch_ready BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS districts (
    district_id TEXT PRIMARY KEY,
    state_id TEXT NOT NULL REFERENCES states(state_id),
    eci_district_code TEXT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assembly_constituencies (
    ac_id TEXT PRIMARY KEY,
    state_id TEXT NOT NULL REFERENCES states(state_id),
    district_id TEXT REFERENCES districts(district_id),
    ac_number INTEGER NOT NULL,
    name TEXT NOT NULL,
    reservation_status TEXT,
    UNIQUE (state_id, ac_number)
);

CREATE TABLE IF NOT EXISTS polling_stations (
    polling_station_id TEXT PRIMARY KEY,
    ac_id TEXT NOT NULL REFERENCES assembly_constituencies(ac_id),
    part_number INTEGER NOT NULL,
    name TEXT,
    address_redacted TEXT,
    source_updated_at DATE,
    UNIQUE (ac_id, part_number)
);

CREATE TABLE IF NOT EXISTS roll_versions (
    roll_version_id TEXT PRIMARY KEY,
    state_id TEXT NOT NULL REFERENCES states(state_id),
    roll_year INTEGER NOT NULL,
    roll_kind TEXT NOT NULL,
    language TEXT,
    source_label TEXT NOT NULL,
    source_url TEXT,
    published_on DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS voter_records (
    voter_record_id TEXT PRIMARY KEY,
    roll_version_id TEXT NOT NULL REFERENCES roll_versions(roll_version_id),
    state_id TEXT NOT NULL REFERENCES states(state_id),
    ac_id TEXT REFERENCES assembly_constituencies(ac_id),
    polling_station_id TEXT REFERENCES polling_stations(polling_station_id),
    serial_number INTEGER,
    name_original TEXT NOT NULL,
    name_normalized TEXT,
    name_phonetic TEXT,
    relation_type TEXT,
    relative_name_normalized TEXT,
    age INTEGER,
    gender TEXT,
    epic_hash TEXT,
    epic_last4 TEXT,
    data_quality TEXT NOT NULL DEFAULT 'ok',
    source_confidence NUMERIC(4,3) NOT NULL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_voter_records_state_ac_name_trgm
    ON voter_records USING GIN (name_normalized gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_voter_records_scoped_lookup
    ON voter_records (state_id, ac_id, polling_station_id, serial_number);
CREATE INDEX IF NOT EXISTS idx_voter_records_epic_hash
    ON voter_records (epic_hash);

CREATE TABLE IF NOT EXISTS source_documents (
    source_document_id TEXT PRIMARY KEY,
    state_id TEXT NOT NULL REFERENCES states(state_id),
    roll_version_id TEXT REFERENCES roll_versions(roll_version_id),
    source_uri TEXT NOT NULL,
    local_path TEXT,
    checksum TEXT,
    parser_hint TEXT,
    status TEXT NOT NULL DEFAULT 'registered',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    extraction_run_id TEXT PRIMARY KEY,
    source_document_id TEXT NOT NULL REFERENCES source_documents(source_document_id),
    parser_name TEXT NOT NULL,
    expected_records INTEGER,
    parsed_records INTEGER,
    quality_summary JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS guidance_rules (
    rule_id TEXT PRIMARY KEY,
    state_id TEXT REFERENCES states(state_id),
    situation TEXT NOT NULL,
    priority TEXT NOT NULL,
    action_template JSONB NOT NULL,
    source_labels TEXT[] NOT NULL DEFAULT '{}'
);
