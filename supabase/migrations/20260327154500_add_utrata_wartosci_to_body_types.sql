-- Migration: add utrata_wartosci to body_types
-- This column will store the base RV correction for each body type.

ALTER TABLE public.body_types ADD COLUMN IF NOT EXISTS utrata_wartosci NUMERIC DEFAULT 0;

COMMENT ON COLUMN public.body_types.utrata_wartosci IS 'Bazowa utrata wartości (korekta RV) dla danego typu nadwozia.';
