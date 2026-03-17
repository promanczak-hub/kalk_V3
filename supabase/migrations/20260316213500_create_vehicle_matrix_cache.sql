-- Create the matrix cache table for fast reverse search pricing logic
CREATE TABLE IF NOT EXISTS public.vehicle_matrix_cache (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES public.vehicle_synthesis(id) ON DELETE CASCADE,
    duration_months INTEGER NOT NULL,
    annual_mileage INTEGER NOT NULL,
    margin_pct NUMERIC(5, 2) NOT NULL,
    base_price_net NUMERIC(12, 2) NOT NULL,
    monthly_price_net NUMERIC(12, 2) NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    
    -- Ensure we only have one cell per vehicle per term per margin
    UNIQUE (vehicle_id, duration_months, annual_mileage, margin_pct)
);

-- Indexes for lightning fast searching and joining
CREATE INDEX IF NOT EXISTS idx_vehicle_matrix_cache_vehicle_id ON public.vehicle_matrix_cache(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_matrix_cache_search ON public.vehicle_matrix_cache(duration_months, annual_mileage, margin_pct, monthly_price_net);
CREATE INDEX IF NOT EXISTS idx_vehicle_matrix_cache_price ON public.vehicle_matrix_cache(monthly_price_net);

-- Enable RLS (allow read for everyone, write for authenticated users/services)
ALTER TABLE public.vehicle_matrix_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow read access to all users for vehicle_matrix_cache" 
ON public.vehicle_matrix_cache FOR SELECT 
USING (true);

CREATE POLICY "Allow write access to authenticated for vehicle_matrix_cache" 
ON public.vehicle_matrix_cache FOR ALL 
USING (auth.role() = 'authenticated');
