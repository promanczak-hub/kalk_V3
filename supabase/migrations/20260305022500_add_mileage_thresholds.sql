-- Migration: Add mileage threshold params to samar_classes
-- These replace hardcoded 140k/190k values in the WR calculator

ALTER TABLE samar_classes ADD COLUMN IF NOT EXISTS base_mileage_km INTEGER DEFAULT 140000;
ALTER TABLE samar_classes ADD COLUMN IF NOT EXISTS mileage_threshold_km INTEGER DEFAULT 190000;
ALTER TABLE samar_classes ADD COLUMN IF NOT EXISTS base_period_months INTEGER DEFAULT 48;

-- Set defaults for all existing rows
UPDATE samar_classes 
SET base_mileage_km = 140000, 
    mileage_threshold_km = 190000, 
    base_period_months = 48
WHERE base_mileage_km IS NULL;
