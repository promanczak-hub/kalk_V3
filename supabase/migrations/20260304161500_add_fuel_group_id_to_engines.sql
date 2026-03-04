-- Migration: Add fuel_group_id to engines table
-- Maps each granular engine type to a WR bucket (1=Benzyna, 2=Diesel, 3=EV/Alternatywne)

ALTER TABLE engines ADD COLUMN IF NOT EXISTS fuel_group_id INTEGER NOT NULL DEFAULT 1;

-- Benzyna-based → bucket 1
UPDATE engines SET fuel_group_id = 1 WHERE name IN ('Benzyna (PB)', 'Benzyna mHEV (PB-mHEV)');

-- Diesel-based → bucket 2
UPDATE engines SET fuel_group_id = 2 WHERE name IN ('Diesel (ON)', 'Diesel mHEV (ON-mHEV)');

-- Alternatywne → bucket 3
UPDATE engines SET fuel_group_id = 3 WHERE name IN (
    'Autogaz (LPG)',
    'Elektryczny (BEV)',
    'Hybryda (HEV)',
    'Hybryda Plug-in (PHEV)',
    'Wodór (FCEV)'
);
