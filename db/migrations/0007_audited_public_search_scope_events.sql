-- Keep every public-search authorization change attributable and reversible.
ALTER TABLE public_search_scopes
    ADD CONSTRAINT public_search_scopes_reviewer_not_blank
    CHECK (btrim(reviewed_by) <> '' AND char_length(reviewed_by) <= 200);

CREATE TABLE IF NOT EXISTS public_search_scope_events (
    event_id TEXT PRIMARY KEY,
    roll_version_id TEXT NOT NULL REFERENCES roll_versions(roll_version_id),
    ac_id TEXT NOT NULL REFERENCES assembly_constituencies(ac_id),
    action TEXT NOT NULL CHECK (action IN ('enable', 'disable')),
    reviewed_by TEXT NOT NULL CHECK (btrim(reviewed_by) <> '' AND char_length(reviewed_by) <= 200),
    reason TEXT NOT NULL CHECK (btrim(reason) <> '' AND char_length(reason) <= 500),
    readiness_snapshot JSONB NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_public_search_scope_events_scope_time
    ON public_search_scope_events (roll_version_id, ac_id, reviewed_at DESC);

CREATE OR REPLACE FUNCTION reject_public_search_scope_event_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'public_search_scope_events is append-only';
END;
$$;

CREATE TRIGGER public_search_scope_events_append_only
    BEFORE UPDATE OR DELETE ON public_search_scope_events
    FOR EACH ROW EXECUTE FUNCTION reject_public_search_scope_event_mutation();
