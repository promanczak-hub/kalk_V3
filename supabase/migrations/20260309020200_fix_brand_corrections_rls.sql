-- Fix RLS policy for ltr_admin_korekta_wr_markas: allow service_role full access
-- The table currently only allows 'authenticated' users, blocking backend seeders

-- Drop restrictive policies
DROP POLICY IF EXISTS "Enable ALL for authenticated users on ltr_admin_korekta_wr_markas" ON public.ltr_admin_korekta_wr_markas;
DROP POLICY IF EXISTS "Enable READ for anon users on ltr_admin_korekta_wr_markas" ON public.ltr_admin_korekta_wr_markas;

-- Create permissive policies
CREATE POLICY "brand_corr_select" ON public.ltr_admin_korekta_wr_markas
    FOR SELECT USING (true);
CREATE POLICY "brand_corr_all" ON public.ltr_admin_korekta_wr_markas
    FOR ALL USING (true) WITH CHECK (true);
