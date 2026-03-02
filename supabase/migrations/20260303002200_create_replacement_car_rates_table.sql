CREATE TABLE IF NOT EXISTS public.replacement_car_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    samar_class_id INTEGER NOT NULL,
    samar_class_name TEXT NOT NULL,
    average_days_per_year NUMERIC(5,2) DEFAULT 6.5 NOT NULL,
    daily_rate_net NUMERIC(10,2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Enable RLS
ALTER TABLE public.replacement_car_rates ENABLE ROW LEVEL SECURITY;

-- Allow read access for authenticated users
CREATE POLICY "Allow read access to authenticated users" ON public.replacement_car_rates
    FOR SELECT
    TO authenticated
    USING (true);

-- Allow all access to service role (from backend)
CREATE POLICY "Allow all access to service role" ON public.replacement_car_rates
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
