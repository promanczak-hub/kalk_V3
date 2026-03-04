-- Migration 20260304003000_create_wr_tables_v3.sql

CREATE TABLE public.samar_base_rv (
    klasa_samar text PRIMARY KEY,
    base_rv_percent numeric NOT NULL
);

CREATE TABLE public.samar_brand_corrections (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar text NOT NULL,
    rodzaj_paliwa text NOT NULL,
    marka text NOT NULL,
    correction_percent numeric NOT NULL,
    UNIQUE(klasa_samar, rodzaj_paliwa, marka)
);

CREATE TABLE public.samar_vintage_depreciation (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar text NOT NULL,
    rodzaj_paliwa text NOT NULL,
    rok integer NOT NULL,
    depreciation_percent numeric NOT NULL,
    UNIQUE(klasa_samar, rodzaj_paliwa, rok)
);

CREATE TABLE public.samar_options_depreciation (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    klasa_samar text NOT NULL,
    rodzaj_paliwa text NOT NULL,
    wiek_w_latach integer NOT NULL,
    depreciation_percent numeric NOT NULL,
    UNIQUE(klasa_samar, rodzaj_paliwa, wiek_w_latach)
);

CREATE TABLE public.samar_mileage_thresholds (
    klasa_samar text PRIMARY KEY,
    threshold_lower integer NOT NULL DEFAULT 140000,
    threshold_upper integer NOT NULL DEFAULT 190000,
    penalty_lower numeric NOT NULL,
    penalty_upper numeric NOT NULL,
    step_km integer NOT NULL DEFAULT 10000
);

CREATE TABLE public.samar_color_depreciation (
    kolor text PRIMARY KEY,
    depreciation_percent numeric NOT NULL
);

CREATE TABLE public.samar_body_depreciation (
    nadwozie_zabudowa text PRIMARY KEY,
    depreciation_percent numeric NOT NULL
);

-- Włącz RLS na nowych tabelach
ALTER TABLE public.samar_base_rv ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_base_rv FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_base_rv FOR ALL USING (auth.role() = 'authenticated');

ALTER TABLE public.samar_brand_corrections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_brand_corrections FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_brand_corrections FOR ALL USING (auth.role() = 'authenticated');

ALTER TABLE public.samar_vintage_depreciation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_vintage_depreciation FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_vintage_depreciation FOR ALL USING (auth.role() = 'authenticated');

ALTER TABLE public.samar_options_depreciation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_options_depreciation FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_options_depreciation FOR ALL USING (auth.role() = 'authenticated');

ALTER TABLE public.samar_mileage_thresholds ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_mileage_thresholds FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_mileage_thresholds FOR ALL USING (auth.role() = 'authenticated');

ALTER TABLE public.samar_color_depreciation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_color_depreciation FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_color_depreciation FOR ALL USING (auth.role() = 'authenticated');

ALTER TABLE public.samar_body_depreciation ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable read access for all users" ON public.samar_body_depreciation FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_body_depreciation FOR ALL USING (auth.role() = 'authenticated');
