-- Create samar_class_base_rv table
CREATE TABLE IF NOT EXISTS public.samar_class_base_rv (
    id SERIAL PRIMARY KEY,
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    engine_type_id INTEGER NOT NULL REFERENCES public.engines(id),
    base_rv_percent NUMERIC NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(samar_class_id, engine_type_id)
);

-- RLS policies
ALTER TABLE public.samar_class_base_rv ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'samar_class_base_rv' AND policyname = 'Allow public read access') THEN
        CREATE POLICY "Allow public read access" ON public.samar_class_base_rv FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'samar_class_base_rv' AND policyname = 'Allow authenticated insert') THEN
        CREATE POLICY "Allow authenticated insert" ON public.samar_class_base_rv FOR INSERT WITH CHECK (auth.role() = 'authenticated');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'samar_class_base_rv' AND policyname = 'Allow authenticated update') THEN
        CREATE POLICY "Allow authenticated update" ON public.samar_class_base_rv FOR UPDATE USING (auth.role() = 'authenticated');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'samar_class_base_rv' AND policyname = 'Allow authenticated delete') THEN
        CREATE POLICY "Allow authenticated delete" ON public.samar_class_base_rv FOR DELETE USING (auth.role() = 'authenticated');
    END IF;
END $$;

-- Seed data

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.31
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.48
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.4
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.44
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.44
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.33
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.56
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - KABRIOLETY/SPORTOWE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - KABRIOLETY/SPORTOWE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - KABRIOLETY/SPORTOWE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - KABRIOLETY/SPORTOWE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.0
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - KABRIOLETY/SPORTOWE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.28
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.31
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.12
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.27
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.28
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.49
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.4
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.33
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.0
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Pick-up - PICK-UP' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.42
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Pick-up - PICK-UP' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Pick-up - PICK-UP' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Pick-up - PICK-UP' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.52
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Pick-up - PICK-UP' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.44
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Dostawcza - 1 OSOB.-DOST. (LAV)' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Dostawcza - 1 OSOB.-DOST. (LAV)' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Dostawcza - 1 OSOB.-DOST. (LAV)' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Dostawcza - 1 OSOB.-DOST. (LAV)' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.44
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Dostawcza - 1 OSOB.-DOST. (LAV)' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Lekkie dostawcze - VAN' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.42
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Lekkie dostawcze - VAN' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Lekkie dostawcze - VAN' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Lekkie dostawcze - VAN' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Lekkie dostawcze - VAN' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.0
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Średnie dostawcze - ŚREDNIE DOSTAWCZE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Średnie dostawcze - ŚREDNIE DOSTAWCZE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Średnie dostawcze - ŚREDNIE DOSTAWCZE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Średnie dostawcze - ŚREDNIE DOSTAWCZE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.0
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Średnie dostawcze - ŚREDNIE DOSTAWCZE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - A MINI' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.31
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - B MAŁE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.39
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.48
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.4
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.44
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.44
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.33
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.41
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - F LUKSUSOWE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.56
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Premium - KABRIOLETY/SPORTOWE' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Premium - KABRIOLETY/SPORTOWE' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Premium - KABRIOLETY/SPORTOWE' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Premium - KABRIOLETY/SPORTOWE' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.0
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Premium - KABRIOLETY/SPORTOWE' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.28
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.31
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.12
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.27
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.28
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Vany - D VANY' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.49
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.4
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - C NIŻSZA ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.46
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.38
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - D ŚREDNIA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.33
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Benzyna'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Diesel'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.18
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Elektryczny'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.32
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda Plug-in'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;

INSERT INTO public.samar_class_base_rv (samar_class_id, engine_type_id, base_rv_percent)
SELECT 
    sc.id, 
    e.id, 
    0.43
FROM public.samar_classes sc
CROSS JOIN public.engines e
WHERE sc.name = 'Podstawowa - E WYŻSZA' AND e.name = 'Hybryda (HEV)'
ON CONFLICT (samar_class_id, engine_type_id) 
DO UPDATE SET base_rv_percent = EXCLUDED.base_rv_percent;
