-- Migration: Add mileage threshold params to samar_classes
-- Guarded: skip if samar_classes does not exist yet

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'samar_classes' AND table_schema = 'public') THEN
        ALTER TABLE samar_classes ADD COLUMN IF NOT EXISTS base_mileage_km INTEGER DEFAULT 140000;
        ALTER TABLE samar_classes ADD COLUMN IF NOT EXISTS mileage_threshold_km INTEGER DEFAULT 190000;
        ALTER TABLE samar_classes ADD COLUMN IF NOT EXISTS base_period_months INTEGER DEFAULT 48;

        UPDATE samar_classes
        SET base_mileage_km = 140000,
            mileage_threshold_km = 190000,
            base_period_months = 48
        WHERE base_mileage_km IS NULL;
    END IF;
END $$;
