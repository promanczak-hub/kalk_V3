-- Add discount_pct column to vehicle_matrix_cache
ALTER TABLE public.vehicle_matrix_cache 
ADD COLUMN discount_pct numeric NOT NULL DEFAULT 0.0;

-- Drop the old unique constraint
ALTER TABLE public.vehicle_matrix_cache 
DROP CONSTRAINT vehicle_matrix_cache_vehicle_id_duration_months_annual_mile_key;

-- Add the new unique constraint
ALTER TABLE public.vehicle_matrix_cache 
ADD CONSTRAINT vehicle_matrix_cache_unique_key 
UNIQUE (vehicle_id, duration_months, annual_mileage, margin_pct, discount_pct);
