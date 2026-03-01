CREATE TABLE IF NOT EXISTS public.ltr_kalkulacje (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numer_kalkulacji VARCHAR NOT NULL UNIQUE,
    status VARCHAR DEFAULT 'szkic_vertex',
    stan_json JSONB,
    dane_pojazdu TEXT,
    cena_netto NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.ltr_kalkulacje ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable ALL for authenticated users on ltr_kalkulacje" ON public.ltr_kalkulacje FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "Enable ALL for anon users on ltr_kalkulacje" ON public.ltr_kalkulacje FOR ALL TO anon USING (true) WITH CHECK (true);
