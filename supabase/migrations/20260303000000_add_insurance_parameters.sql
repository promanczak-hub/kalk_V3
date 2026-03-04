-- Migration: Add NNW, ASS, Zielona Karta parameters to control_center

ALTER TABLE control_center
ADD COLUMN IF NOT EXISTS ins_nnw_annual_rate NUMERIC DEFAULT 150.0,
ADD COLUMN IF NOT EXISTS ins_ass_annual_rate NUMERIC DEFAULT 200.0,
ADD COLUMN IF NOT EXISTS ins_green_card_annual_rate NUMERIC DEFAULT 50.0;
