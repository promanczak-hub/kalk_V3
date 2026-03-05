-- Add permissive RLS policies for replacement_car_rates
-- (matches pattern of other CRUD tables like samar_service_costs, tyre_costs, etc.)

-- Drop restrictive policies
DROP POLICY IF EXISTS "Allow read access to authenticated users" ON public.replacement_car_rates;
DROP POLICY IF EXISTS "Allow all access to service role" ON public.replacement_car_rates;

-- Allow full access to all roles (anon, authenticated, service_role)
CREATE POLICY "Allow full access to all roles" ON public.replacement_car_rates
    FOR ALL
    USING (true)
    WITH CHECK (true);
