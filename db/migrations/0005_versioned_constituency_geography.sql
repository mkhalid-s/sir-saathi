-- Prevent historical and current constituencies with reused AC numbers from overwriting each other.
ALTER TABLE assembly_constituencies
    ADD COLUMN IF NOT EXISTS geography_version TEXT;

UPDATE assembly_constituencies
SET geography_version = 'legacy-unversioned'
WHERE geography_version IS NULL;

ALTER TABLE assembly_constituencies
    ALTER COLUMN geography_version SET NOT NULL,
    ALTER COLUMN geography_version DROP DEFAULT;

ALTER TABLE assembly_constituencies
    DROP CONSTRAINT IF EXISTS assembly_constituencies_state_id_ac_number_key;

ALTER TABLE assembly_constituencies
    ADD CONSTRAINT assembly_constituencies_state_ac_geography_version_key
    UNIQUE (state_id, ac_number, geography_version);
