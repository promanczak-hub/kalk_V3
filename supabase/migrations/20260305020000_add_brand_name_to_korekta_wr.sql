-- Migration: Add brand_name columns for LLM-driven brand correction lookup
-- Guarded: skip if ltr_admin_korekta_wr_markas does not exist yet

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ltr_admin_korekta_wr_markas' AND table_schema = 'public') THEN
        RETURN;
    END IF;

    ALTER TABLE ltr_admin_korekta_wr_markas ADD COLUMN IF NOT EXISTS brand_name TEXT;
    ALTER TABLE ltr_admin_korekta_wr_markas ADD COLUMN IF NOT EXISTS model_name TEXT;
    ALTER TABLE ltr_admin_korekta_wr_markas ADD COLUMN IF NOT EXISTS notes TEXT;

    CREATE INDEX IF NOT EXISTS idx_korekta_wr_brand_name
      ON ltr_admin_korekta_wr_markas(brand_name);

    ALTER TABLE ltr_admin_korekta_wr_markas
      DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_pkey;

    ALTER TABLE ltr_admin_korekta_wr_markas
      ALTER COLUMN marka_id DROP NOT NULL;
END $$;
