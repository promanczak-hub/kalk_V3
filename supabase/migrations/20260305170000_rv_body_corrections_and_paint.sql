-- Migration: RV body type corrections, paint wr_correction, rocznik seed
-- Part of Calc 06 Utrata Wartości — Excel JŁ parity

-- ═══════════════════════════════════════════════════════════════════
-- 1. Rozszerzenie body_types o brakujące kategorie z wymagań
-- ═══════════════════════════════════════════════════════════════════

INSERT INTO public.body_types (name, vehicle_class, description) VALUES
    ('2 drzwiowy', 'Osobowy', 'Osobowy 2 drzwiowy'),
    ('3 drzwiowy', 'Osobowy', 'Osobowy 3 drzwiowy'),
    ('Kombi Dostawczy', 'Dostawczy', 'Dostawczy Kombi')
ON CONFLICT (name) DO NOTHING;

-- ═══════════════════════════════════════════════════════════════════
-- 2. Tabela body_type_wr_corrections (klasa × marka × body_type)
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.body_type_wr_corrections (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id),
    brand_name TEXT NOT NULL DEFAULT '',
    body_type_id INTEGER NOT NULL REFERENCES public.body_types(id),
    correction_percent NUMERIC(6,4) NOT NULL DEFAULT 0,
    zabudowa_correction_percent NUMERIC(6,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(samar_class_id, brand_name, body_type_id)
);

COMMENT ON TABLE public.body_type_wr_corrections IS
    'Korekty WR za typ nadwozia: per klasa SAMAR × marka × body_type. Default 0 wszędzie.';

COMMENT ON COLUMN public.body_type_wr_corrections.correction_percent IS
    'Korekta % WR za typ nadwozia (np. Px=+0.04, ND=0)';

COMMENT ON COLUMN public.body_type_wr_corrections.zabudowa_correction_percent IS
    'Dodatkowa korekta aprecjacji WR dla pojazdów z zabudową zmieniającą przeznaczenie (plandeka, skrzynia, wywrotka, dodatkowy rząd miejsc)';

ALTER TABLE public.body_type_wr_corrections ENABLE ROW LEVEL SECURITY;

CREATE POLICY "body_type_wr_select" ON public.body_type_wr_corrections
    FOR SELECT USING (true);

CREATE POLICY "body_type_wr_all_auth" ON public.body_type_wr_corrections
    FOR ALL USING (auth.role() = 'authenticated');

-- ═══════════════════════════════════════════════════════════════════
-- 3. Dodanie wr_correction do paint_types
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.paint_types
    ADD COLUMN IF NOT EXISTS wr_correction NUMERIC(6,4) DEFAULT 0;

COMMENT ON COLUMN public.paint_types.wr_correction IS
    'Korekta WR za typ lakieru: metalik=0, niemetalik=-0.01';

-- Seed: metalik=0, niemetalik=-0.01 (z Excela KOLOR)
UPDATE public.paint_types SET wr_correction = 0 WHERE name ILIKE '%metaliz%' OR name ILIKE '%metal%';
UPDATE public.paint_types SET wr_correction = -0.01 WHERE name ILIKE '%niemetaliz%' OR name ILIKE '%bazow%';
-- Perłowy traktujemy jak metalik
UPDATE public.paint_types SET wr_correction = 0 WHERE name ILIKE '%perło%';

-- ═══════════════════════════════════════════════════════════════════
-- 4. Seed: korekty rocznika (z Excela ROCZNIK)
-- ═══════════════════════════════════════════════════════════════════

UPDATE public.ltr_admin_korekta_wr_roczniks
    SET korekta_procent = 0.0 WHERE rocznik ILIKE '%bieżący%' AND rocznik NOT ILIKE '%-1%';

UPDATE public.ltr_admin_korekta_wr_roczniks
    SET korekta_procent = -0.08 WHERE rocznik ILIKE '%bieżący-1%' OR rocznik ILIKE '%-1%';

-- ═══════════════════════════════════════════════════════════════════
-- 5. Dodanie flagi zabudowa_apr_wr do vehicle_synthesis
-- ═══════════════════════════════════════════════════════════════════

ALTER TABLE public.vehicle_synthesis
    ADD COLUMN IF NOT EXISTS zabudowa_apr_wr BOOLEAN DEFAULT false;

COMMENT ON COLUMN public.vehicle_synthesis.zabudowa_apr_wr IS
    'Flaga: pojazd z zabudową zmieniającą przeznaczenie (aprecjacja WR). Ustawiana przez LLM lub ręcznie.';
