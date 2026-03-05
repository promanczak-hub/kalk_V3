-- Migration: 1:1 Engine-to-WR mapping (Option B)
-- Changes fuel_type_id from 3-bucket system to direct FK → engines(id)
-- Tables are currently empty so no data migration needed.

-- 1. Add FK constraint to samar_class_depreciation_rates
ALTER TABLE public.samar_class_depreciation_rates
    ADD CONSTRAINT fk_depreciation_engine
    FOREIGN KEY (fuel_type_id) REFERENCES public.engines(id) ON DELETE CASCADE;

-- 2. Add FK constraint to samar_class_mileage_corrections
ALTER TABLE public.samar_class_mileage_corrections
    ADD CONSTRAINT fk_mileage_engine
    FOREIGN KEY (fuel_type_id) REFERENCES public.engines(id) ON DELETE CASCADE;

-- 3. Drop fuel_group_id from engines (no longer needed)
ALTER TABLE public.engines DROP COLUMN IF EXISTS fuel_group_id;

-- 4. Update unique constraints to use new semantic
-- (already UNIQUE on samar_class_id, fuel_type_id, year) — stays the same,
-- just now fuel_type_id references engines.id (1-9) instead of bucket (1-3)
