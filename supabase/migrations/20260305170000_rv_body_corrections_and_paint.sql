-- Migration: RV body type corrections, paint wr_correction, rocznik seed
-- Guarded: skip sections if dependent tables do not exist yet

-- 1. body_types inserts (guarded)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'body_types' AND table_schema = 'public') THEN
        INSERT INTO public.body_types (name, vehicle_class, description) VALUES
            ('2 drzwiowy', 'Osobowy', 'Osobowy 2 drzwiowy'),
            ('3 drzwiowy', 'Osobowy', 'Osobowy 3 drzwiowy'),
            ('Kombi Dostawczy', 'Dostawczy', 'Dostawczy Kombi')
        ON CONFLICT (name) DO NOTHING;
    END IF;
END $$;

-- 2. body_type_wr_corrections table (guarded on samar_classes + body_types)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'samar_classes' AND table_schema = 'public')
       AND EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'body_types' AND table_schema = 'public')
    THEN
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

        ALTER TABLE public.body_type_wr_corrections ENABLE ROW LEVEL SECURITY;

        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'body_type_wr_select' AND tablename = 'body_type_wr_corrections') THEN
            CREATE POLICY "body_type_wr_select" ON public.body_type_wr_corrections FOR SELECT USING (true);
        END IF;

        IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'body_type_wr_all_auth' AND tablename = 'body_type_wr_corrections') THEN
            CREATE POLICY "body_type_wr_all_auth" ON public.body_type_wr_corrections FOR ALL USING (auth.role() = 'authenticated');
        END IF;
    END IF;
END $$;

-- 3. paint_types wr_correction (guarded)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'paint_types' AND table_schema = 'public') THEN
        ALTER TABLE public.paint_types ADD COLUMN IF NOT EXISTS wr_correction NUMERIC(6,4) DEFAULT 0;
        UPDATE public.paint_types SET wr_correction = 0 WHERE name ILIKE '%metaliz%' OR name ILIKE '%metal%';
        UPDATE public.paint_types SET wr_correction = -0.01 WHERE name ILIKE '%niemetaliz%' OR name ILIKE '%bazow%';
        UPDATE public.paint_types SET wr_correction = 0 WHERE name ILIKE '%perło%';
    END IF;
END $$;

-- 4. Rocznik corrections (guarded)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'ltr_admin_korekta_wr_roczniks' AND table_schema = 'public') THEN
        UPDATE public.ltr_admin_korekta_wr_roczniks SET korekta_procent = 0.0 WHERE rocznik ILIKE '%bieżący%' AND rocznik NOT ILIKE '%-1%';
        UPDATE public.ltr_admin_korekta_wr_roczniks SET korekta_procent = -0.08 WHERE rocznik ILIKE '%bieżący-1%' OR rocznik ILIKE '%-1%';
    END IF;
END $$;

-- 5. vehicle_synthesis flag (guarded)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'vehicle_synthesis' AND table_schema = 'public') THEN
        ALTER TABLE public.vehicle_synthesis ADD COLUMN IF NOT EXISTS zabudowa_apr_wr BOOLEAN DEFAULT false;
    END IF;
END $$;
