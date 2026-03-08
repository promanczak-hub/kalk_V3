-- Migration: Add fuel_group_id to engines table
-- Maps each granular engine type to a WR bucket (1=Benzyna, 2=Diesel, 3=EV/Alternatywne)
-- Guarded: skip if engines table does not exist yet

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'engines' AND table_schema = 'public') THEN
        ALTER TABLE engines ADD COLUMN IF NOT EXISTS fuel_group_id INTEGER NOT NULL DEFAULT 1;

        UPDATE engines SET fuel_group_id = 1 WHERE name IN ('Benzyna (PB)', 'Benzyna mHEV (PB-mHEV)');
        UPDATE engines SET fuel_group_id = 2 WHERE name IN ('Diesel (ON)', 'Diesel mHEV (ON-mHEV)');
        UPDATE engines SET fuel_group_id = 3 WHERE name IN (
            'Autogaz (LPG)',
            'Elektryczny (BEV)',
            'Hybryda (HEV)',
            'Hybryda Plug-in (PHEV)',
            'Wodór (FCEV)'
        );
    END IF;
END $$;
