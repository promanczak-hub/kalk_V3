-- Migration: 1:1 Engine-to-WR mapping (Option B)
-- Changes fuel_type_id from 3-bucket system to direct FK → engines(id)
-- Guarded: skip if dependent tables do not exist yet

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'engines' AND table_schema = 'public')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'samar_class_depreciation_rates' AND table_schema = 'public')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'samar_class_mileage_corrections' AND table_schema = 'public')
    THEN
        -- 1. Add FK constraint to samar_class_depreciation_rates
        IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_depreciation_engine') THEN
            ALTER TABLE public.samar_class_depreciation_rates
                ADD CONSTRAINT fk_depreciation_engine
                FOREIGN KEY (fuel_type_id) REFERENCES public.engines(id) ON DELETE CASCADE;
        END IF;

        -- 2. Add FK constraint to samar_class_mileage_corrections
        IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name = 'fk_mileage_engine') THEN
            ALTER TABLE public.samar_class_mileage_corrections
                ADD CONSTRAINT fk_mileage_engine
                FOREIGN KEY (fuel_type_id) REFERENCES public.engines(id) ON DELETE CASCADE;
        END IF;

        -- 3. Drop fuel_group_id from engines (no longer needed)
        ALTER TABLE public.engines DROP COLUMN IF EXISTS fuel_group_id;
    END IF;
END $$;
