-- Add Tyre Costs to Control Center
ALTER TABLE public.control_center ADD COLUMN IF NOT EXISTS cost_tyre_swap NUMERIC DEFAULT 0;
ALTER TABLE public.control_center ADD COLUMN IF NOT EXISTS cost_tyre_storage NUMERIC DEFAULT 0;

-- Update the default row
UPDATE public.control_center SET cost_tyre_swap = 120, cost_tyre_storage = 216 WHERE id = 1;
