-- Migration: zabudowa_types dictionary + zabudowa_wr_corrections + engine_type_id
-- Purpose: Granular zabudowa (body modification) corrections instead of flat Px=4%

-- ═══════════════════════════════════════════════════════════════════
-- 1. zabudowa_types — słownik typów zabudowy
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.zabudowa_types (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    excel_code TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.zabudowa_types ENABLE ROW LEVEL SECURITY;
CREATE POLICY "zabudowa_types_select" ON public.zabudowa_types FOR SELECT USING (true);
CREATE POLICY "zabudowa_types_all_auth" ON public.zabudowa_types FOR ALL USING (auth.role() = 'authenticated');

-- Seed dictionary
INSERT INTO public.zabudowa_types (name, description, excel_code) VALUES
    ('Standard (P)',        'Furgon bazowy — brak dodatkowej zabudowy', 'P'),
    ('Chłodnia',            'Zabudowa chłodnicza',                     'Px'),
    ('Izoterma',            'Zabudowa izotermiczna',                   'Px'),
    ('Kontener',            'Zabudowa kontenerowa',                    'Px'),
    ('Plandeka',            'Zabudowa z plandeką',                     'Px'),
    ('Brygadówka',          'Zabudowa brygadowa',                      'Px'),
    ('Laweta',              'Zabudowa laweta',                         'Px'),
    ('Wywrotka',            'Zabudowa wywrotkowa',                     'Px'),
    ('Warsztat',            'Zabudowa warsztatowa',                    'Px'),
    ('Zabudowa specjalna',  'Inna zabudowa niestandardowa',            'Px');

-- ═══════════════════════════════════════════════════════════════════
-- 2. zabudowa_wr_corrections — korekty WR per zabudowa × klasa
-- ═══════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS public.zabudowa_wr_corrections (
    id SERIAL PRIMARY KEY,
    zabudowa_type_id INTEGER NOT NULL REFERENCES public.zabudowa_types(id) ON DELETE CASCADE,
    samar_class_id INTEGER REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    correction_percent NUMERIC(6,4) NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(zabudowa_type_id, samar_class_id)
);

ALTER TABLE public.zabudowa_wr_corrections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "zabudowa_wr_select" ON public.zabudowa_wr_corrections FOR SELECT USING (true);
CREATE POLICY "zabudowa_wr_all_auth" ON public.zabudowa_wr_corrections FOR ALL USING (auth.role() = 'authenticated');

-- Seed: Standard=0%, all Px types=4% (global — samar_class_id IS NULL)
INSERT INTO public.zabudowa_wr_corrections (zabudowa_type_id, samar_class_id, correction_percent)
SELECT id, NULL, CASE WHEN excel_code = 'P' THEN 0.0 ELSE 0.04 END
FROM public.zabudowa_types;

-- ═══════════════════════════════════════════════════════════════════
-- 3. engine_type_id on body_type_wr_corrections (guarded)
-- ═══════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_name = 'body_type_wr_corrections' AND table_schema = 'public') THEN
        ALTER TABLE public.body_type_wr_corrections
            ADD COLUMN IF NOT EXISTS engine_type_id INTEGER;
    END IF;
END $$;

-- ═══════════════════════════════════════════════════════════════════
-- 4. Update legacy ltr_admin_korekta_wr_zabudowas Px correction
-- ═══════════════════════════════════════════════════════════════════

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_name = 'ltr_admin_korekta_wr_zabudowas' AND table_schema = 'public') THEN
        UPDATE public.ltr_admin_korekta_wr_zabudowas
            SET korekta_procent = 0.04 WHERE rodzaj_zabudowy = 'Px';
    END IF;
END $$;
