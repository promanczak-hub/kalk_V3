-- Persistent saved filter sets for Reverse Search.
-- Stores the full frontend state JSON so a user can name a search ("klient X — flota osobowa")
-- and reload it later. Multi-user keyed by user_email (nullable until auth context arrives).

CREATE TABLE IF NOT EXISTS public.reverse_search_saved_filters (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_email text,
    name text NOT NULL,
    description text,
    filter_state jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL DEFAULT now(),
    updated_at timestamp with time zone NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_saved_filter_per_user_name
    ON public.reverse_search_saved_filters (COALESCE(user_email, ''), name);

CREATE INDEX IF NOT EXISTS idx_saved_filter_user
    ON public.reverse_search_saved_filters (user_email)
    WHERE user_email IS NOT NULL;

CREATE OR REPLACE FUNCTION public.touch_reverse_search_saved_filters()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_touch_reverse_search_saved_filters
    ON public.reverse_search_saved_filters;

CREATE TRIGGER trg_touch_reverse_search_saved_filters
    BEFORE UPDATE ON public.reverse_search_saved_filters
    FOR EACH ROW EXECUTE FUNCTION public.touch_reverse_search_saved_filters();

ALTER TABLE public.reverse_search_saved_filters ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all on reverse_search_saved_filters"
    ON public.reverse_search_saved_filters;

CREATE POLICY "Allow all on reverse_search_saved_filters"
    ON public.reverse_search_saved_filters
    FOR ALL USING (true) WITH CHECK (true);

GRANT ALL ON TABLE public.reverse_search_saved_filters TO anon, authenticated, service_role;

COMMENT ON TABLE public.reverse_search_saved_filters IS
    'User-saved Reverse Search filter sets. filter_state is the full frontend state JSON: {globalSearchQuery, activeFilters[], bodyTypes[], vehicleScope, priceMin, priceMax, priceMonths, priceMileage, priceDepositPct, priceMarginPct}.';
