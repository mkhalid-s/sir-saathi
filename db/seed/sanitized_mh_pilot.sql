-- Sanitized pilot seed shape only. These are not real voter records.
INSERT INTO states (state_id, eci_state_code, name, default_language, data_capability, public_launch_ready)
VALUES ('IN-MH', 'S13', 'Maharashtra', 'mr', 'pilot_indexed_search', false)
ON CONFLICT (state_id) DO NOTHING;

-- Real voter rows must be loaded from ignored local data only after validation.
