-- Ustalone progi przebiegowe dla opon
CREATE TABLE IF NOT EXISTS public.tyre_configurations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  config_key TEXT UNIQUE NOT NULL,
  config_value NUMERIC NOT NULL,
  description TEXT
);

ALTER TABLE public.tyre_configurations ENABLE ROW LEVEL SECURITY;

DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'tyre_configurations' AND policyname = 'Allow public read access for tyre_configurations'
  ) THEN
    CREATE POLICY "Allow public read access for tyre_configurations" ON public.tyre_configurations FOR SELECT USING (true);
  END IF;
  
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename = 'tyre_configurations' AND policyname = 'Allow public update access for tyre_configurations'
  ) THEN
    CREATE POLICY "Allow public update access for tyre_configurations" ON public.tyre_configurations FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

INSERT INTO public.tyre_configurations (config_key, config_value, description)
VALUES
  ('all_season_threshold_1', 60000, 'Limit przebiegu dla 1 kompletu opon wielosezonowych'),
  ('all_season_threshold_2', 120000, 'Limit przebiegu dla 2 kompletów opon wielosezonowych'),
  ('all_season_threshold_3', 180000, 'Limit przebiegu dla 3 kompletów opon wielosezonowych'),
  ('all_season_threshold_4', 240000, 'Limit przebiegu dla 4 kompletów opon wielosezonowych'),
  ('all_season_threshold_5', 300000, 'Limit przebiegu dla 5 kompletów opon wielosezonowych'),
  ('season_threshold_1', 120000, 'Limit przebiegu dla 1 kompletu opon sezonowych'),
  ('season_threshold_2', 180000, 'Limit przebiegu dla 2 kompletów opon sezonowych'),
  ('season_threshold_3', 240000, 'Limit przebiegu dla 3 kompletów opon sezonowych'),
  ('season_threshold_4', 300000, 'Limit przebiegu dla 4 kompletów opon sezonowych')
ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value;
