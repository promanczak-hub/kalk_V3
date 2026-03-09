-- Fix brand corrections: clear old marka_id-based data, add proper unique constraint

-- 1. Drop old PK (was changed by earlier migration)
-- Already done in 20260305020000

-- 2. Delete old V1 data that uses marka_id instead of brand_name
DELETE FROM public.ltr_admin_korekta_wr_markas WHERE brand_name IS NULL;

-- 3. Add unique constraint for upsert
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'uq_brand_correction_class_fuel_brand'
          AND table_name = 'ltr_admin_korekta_wr_markas'
    ) THEN
        ALTER TABLE public.ltr_admin_korekta_wr_markas
            ADD CONSTRAINT uq_brand_correction_class_fuel_brand
            UNIQUE (klasa_wr_id, rodzaj_paliwa, brand_name);
    END IF;
END $$;

-- 4. Make brand_name NOT NULL for future inserts
-- (skip for now — let seeder populate first)
