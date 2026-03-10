-- Create engines table (missing from original migrations)
CREATE TABLE IF NOT EXISTS public.engines (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    category TEXT NOT NULL DEFAULT 'spalinowy',
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.engines ENABLE ROW LEVEL SECURITY;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'engines' AND policyname = 'engines_select'
    ) THEN
        CREATE POLICY "engines_select" ON public.engines FOR SELECT USING (true);
    END IF;
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE schemaname = 'public' AND tablename = 'engines' AND policyname = 'engines_all_auth'
    ) THEN
        CREATE POLICY "engines_all_auth" ON public.engines FOR ALL USING (auth.role() = 'authenticated');
    END IF;
END $$;

-- Seed 9 engine types matching V1
INSERT INTO public.engines (id, name, category) VALUES
    (1, 'Benzyna (PB)',             'spalinowy'),
    (2, 'Diesel (ON)',              'spalinowy'),
    (3, 'Benzyna mHEV (PB-mHEV)',  'mhev'),
    (4, 'Diesel mHEV (ON-mHEV)',   'mhev'),
    (5, 'Hybryda (HEV)',            'hybryda'),
    (6, 'Plug-in Hybrid (PHEV)',    'phev'),
    (7, 'Elektryczny (BEV)',        'ev'),
    (8, 'Wodór (FCEV)',             'ev'),
    (9, 'LPG',                      'spalinowy')
ON CONFLICT (id) DO NOTHING;

-- Reset sequence
SELECT setval('engines_id_seq', (SELECT COALESCE(MAX(id), 0) FROM engines) + 1);
