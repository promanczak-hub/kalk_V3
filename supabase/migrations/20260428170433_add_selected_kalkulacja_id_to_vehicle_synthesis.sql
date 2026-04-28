-- Add user-selected default calculation per vehicle.
-- /search reads this to show the user-chosen "snapshot" calculation;
-- when NULL the backend falls back to the most recent calculation.
ALTER TABLE public.vehicle_synthesis
  ADD COLUMN IF NOT EXISTS selected_kalkulacja_id UUID
    REFERENCES public.ltr_kalkulacje(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS vehicle_synthesis_selected_kalkulacja_id_idx
  ON public.vehicle_synthesis (selected_kalkulacja_id)
  WHERE selected_kalkulacja_id IS NOT NULL;
