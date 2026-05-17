-- Extend vehicle_matrix_cache with cost decomposition for the comparison-chart view.
-- Each row already stores monthly_price_net (= LacznaStawka). We add per-cell totals
-- for the period (NOT monthly) for each cost component so the UI can derive
-- amortyzacja/serwis/opony/ubezpieczenie per month and the WR% snapshot.

ALTER TABLE public.vehicle_matrix_cache
    ADD COLUMN IF NOT EXISTS utrata_wartosci_pln  NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS koszty_serwisowe_pln NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS koszt_opon_pln       NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS ubezpieczenie_pln    NUMERIC(12, 2),
    ADD COLUMN IF NOT EXISTS wr_pct               NUMERIC(6, 2);

CREATE INDEX IF NOT EXISTS idx_vehicle_matrix_cache_vehicle_term_mileage
    ON public.vehicle_matrix_cache (vehicle_id, duration_months, annual_mileage);
