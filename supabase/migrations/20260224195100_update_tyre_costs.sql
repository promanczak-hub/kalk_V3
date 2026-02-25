-- Utworzenie płaskiej tabeli tyre_costs na podstawie klas z cennika LTR
CREATE TABLE IF NOT EXISTS public.tyre_costs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tyre_class TEXT NOT NULL,
  diameter INTEGER NOT NULL DEFAULT 15,
  purchase_price NUMERIC NOT NULL DEFAULT 0.0,
  buyback_price NUMERIC NOT NULL DEFAULT 0.0,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Odblokowanie i ustawienie trybu RLS
ALTER TABLE public.tyre_costs ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'tyre_costs' AND policyname = 'Allow public read access for tyre_costs'
  ) THEN
    CREATE POLICY "Allow public read access for tyre_costs" ON public.tyre_costs FOR SELECT USING (true);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'tyre_costs' AND policyname = 'Allow public update access for tyre_costs'
  ) THEN
    CREATE POLICY "Allow public update access for tyre_costs" ON public.tyre_costs FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

