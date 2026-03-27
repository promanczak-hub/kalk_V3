-- Create Tabela Okres Final
CREATE TABLE IF NOT EXISTS public.tab_okres_final (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    samar_class VARCHAR NOT NULL,
    engine_type VARCHAR NOT NULL,
    year_0 NUMERIC NOT NULL DEFAULT 0,
    year_1 NUMERIC NOT NULL DEFAULT 0,
    year_2 NUMERIC NOT NULL DEFAULT 0,
    year_3 NUMERIC NOT NULL DEFAULT 0,
    year_4 NUMERIC NOT NULL DEFAULT 0,
    year_5 NUMERIC NOT NULL DEFAULT 0,
    year_6 NUMERIC NOT NULL DEFAULT 0,
    year_7 NUMERIC NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(samar_class, engine_type)
);

-- Enable RLS
ALTER TABLE public.tab_okres_final ENABLE ROW LEVEL SECURITY;

-- Create policies (assuming read-only for anon, full for authenticated based on typical setup, but let's just make it fully open for authenticated)
CREATE POLICY "Enable read access for all users" ON public.tab_okres_final FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users only" ON public.tab_okres_final FOR INSERT WITH CHECK (auth.role() = 'authenticated');
CREATE POLICY "Enable update for authenticated users only" ON public.tab_okres_final FOR UPDATE USING (auth.role() = 'authenticated');
CREATE POLICY "Enable delete for authenticated users only" ON public.tab_okres_final FOR DELETE USING (auth.role() = 'authenticated');
