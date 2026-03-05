-- Migration: Add brand_name text column for LLM-driven brand correction lookup
-- Replaces hardcoded brand sets in Python code

ALTER TABLE ltr_admin_korekta_wr_markas
  ADD COLUMN IF NOT EXISTS brand_name TEXT;

ALTER TABLE ltr_admin_korekta_wr_markas
  ADD COLUMN IF NOT EXISTS model_name TEXT;

ALTER TABLE ltr_admin_korekta_wr_markas
  ADD COLUMN IF NOT EXISTS notes TEXT;

-- Index for fast text-based lookup
CREATE INDEX IF NOT EXISTS idx_korekta_wr_brand_name
  ON ltr_admin_korekta_wr_markas(brand_name);

-- Drop old unique constraint that requires marka_id (if exists)
-- and add new one allowing brand_name-based records
ALTER TABLE ltr_admin_korekta_wr_markas
  DROP CONSTRAINT IF EXISTS ltr_admin_korekta_wr_markas_pkey;

-- Make marka_id nullable (no longer required for new brand_name records)
ALTER TABLE ltr_admin_korekta_wr_markas
  ALTER COLUMN marka_id DROP NOT NULL;
