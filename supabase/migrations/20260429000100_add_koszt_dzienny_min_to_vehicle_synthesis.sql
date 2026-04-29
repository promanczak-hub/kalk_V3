ALTER TABLE public.vehicle_synthesis
  ADD COLUMN IF NOT EXISTS koszt_dzienny_min NUMERIC DEFAULT NULL;
