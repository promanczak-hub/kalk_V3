-- Multi-select calculations per vehicle.
-- Existing single-select column `selected_kalkulacja_id` is preserved as the
-- "primary" pick (always equals selected_kalkulacja_ids[1]) for backward compat;
-- new code reads/writes `selected_kalkulacja_ids` (array, no upper limit).

ALTER TABLE public.vehicle_synthesis
  ADD COLUMN IF NOT EXISTS selected_kalkulacja_ids UUID[] NOT NULL DEFAULT '{}'::uuid[];

-- Backfill from the legacy single column so previously-pinned calcs stay pinned.
UPDATE public.vehicle_synthesis
   SET selected_kalkulacja_ids = ARRAY[selected_kalkulacja_id]
 WHERE selected_kalkulacja_id IS NOT NULL
   AND (selected_kalkulacja_ids IS NULL OR selected_kalkulacja_ids = '{}'::uuid[]);

CREATE INDEX IF NOT EXISTS vehicle_synthesis_selected_kalkulacja_ids_idx
  ON public.vehicle_synthesis USING GIN (selected_kalkulacja_ids)
  WHERE array_length(selected_kalkulacja_ids, 1) > 0;
