-- Migration: Update brand correction unique index to include optional model_name
-- Purpose: allow specific model fallbacks while avoiding duplicate conflicts

DO $$
BEGIN
    -- Drop the old constraint that didn't include model_name
    ALTER TABLE public.ltr_admin_korekta_wr_markas
        DROP CONSTRAINT IF EXISTS uq_brand_correction_class_fuel_brand;

    -- Create a new unique index using COALESCE to treat NULL models as a wildcard
    -- We use an index instead of a constraint because constraints cannot contain expressions like COALESCE directly.
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'uidx_brand_correction_class_fuel_brand_model'
          AND n.nspname = 'public'
    ) THEN
        CREATE UNIQUE INDEX uidx_brand_correction_class_fuel_brand_model
            ON public.ltr_admin_korekta_wr_markas (
                samar_class_id, 
                rodzaj_paliwa, 
                brand_name, 
                COALESCE(NULLIF(TRIM(model_name), ''), '*')
            );
    END IF;
END $$;
