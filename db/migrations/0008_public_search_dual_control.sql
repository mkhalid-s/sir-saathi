-- Attribute scope changes to their operator and enforce independent review for enables.
-- Existing enabled scopes predate this evidence and are revoked fail-closed.
ALTER TABLE public_search_scope_events
    ADD COLUMN operated_by TEXT;

UPDATE public_search_scope_events
SET operated_by = 'legacy-event-operator-not-recorded'
WHERE operated_by IS NULL;

ALTER TABLE public_search_scope_events
    ALTER COLUMN operated_by SET NOT NULL,
    ADD CONSTRAINT public_search_scope_events_operator_valid
        CHECK (btrim(operated_by) <> '' AND char_length(operated_by) <= 200),
    ADD CONSTRAINT public_search_scope_events_enable_dual_control
        CHECK (action <> 'enable' OR lower(btrim(operated_by)) <> lower(btrim(reviewed_by)));

ALTER TABLE public_search_scopes
    ADD COLUMN operated_by TEXT;

UPDATE public_search_scopes
SET operated_by = 'legacy-event-operator-not-recorded'
WHERE operated_by IS NULL;

INSERT INTO public_search_scope_events (
    event_id, roll_version_id, ac_id, action, operated_by, reviewed_by, reason, readiness_snapshot
)
SELECT
    'scope-event-migration-0008-' || md5(roll_version_id || ':' || ac_id),
    roll_version_id,
    ac_id,
    'disable',
    'migration-0008-fail-closed',
    reviewed_by,
    'Automatically disabled because the prior enable event did not record a distinct operator.',
    jsonb_build_object(
        'safe_aggregate_report', true,
        'ready_to_enable', false,
        'migration', '0008_public_search_dual_control',
        'blockers', jsonb_build_array('scope requires a new independently reviewed enable decision')
    )
FROM public_search_scopes
WHERE enabled;

UPDATE public_search_scopes
SET enabled = FALSE,
    operated_by = 'migration-0008-fail-closed'
WHERE enabled;

ALTER TABLE public_search_scopes
    ALTER COLUMN operated_by SET NOT NULL,
    ADD CONSTRAINT public_search_scopes_operator_valid
        CHECK (btrim(operated_by) <> '' AND char_length(operated_by) <= 200),
    ADD CONSTRAINT public_search_scopes_enable_dual_control
        CHECK (NOT enabled OR lower(btrim(operated_by)) <> lower(btrim(reviewed_by)));
