-- Migration: Add przewidywana_cena_sprzedazy_lo to control_center
-- Default 0.15 (15%) — coefficient for WRdlaLO = WR × (1 + lo_param)

ALTER TABLE public.control_center
    ADD COLUMN IF NOT EXISTS przewidywana_cena_sprzedazy_lo NUMERIC(6,4) NOT NULL DEFAULT 0.15;

COMMENT ON COLUMN public.control_center.przewidywana_cena_sprzedazy_lo
    IS 'Współczynnik podwyższenia WR dla ceny sprzedaży LO (np. 0.15 = 15%)';
