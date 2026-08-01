-- Add public-source provenance to geographic reference rows.
ALTER TABLE districts
    ADD COLUMN IF NOT EXISTS source_label TEXT,
    ADD COLUMN IF NOT EXISTS source_updated_at DATE;

ALTER TABLE assembly_constituencies
    ADD COLUMN IF NOT EXISTS source_label TEXT,
    ADD COLUMN IF NOT EXISTS source_updated_at DATE;
