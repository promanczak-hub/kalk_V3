-- Migration: create transmission_types dictionary table
-- Replaces hardcoded TRANSMISSION_OPTIONS in VehicleBaseInfo.tsx
-- SOT: Google Sheet 'transmission_dict' tab in Szablon_Wyceny_GCP

CREATE TABLE IF NOT EXISTS public.transmission_types (
    id integer PRIMARY KEY,
    name text NOT NULL UNIQUE
);

ALTER TABLE public.transmission_types ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all users"
    ON public.transmission_types FOR SELECT USING (true);

CREATE POLICY "Enable all access for authenticated users"
    ON public.transmission_types FOR ALL USING (auth.role() = 'authenticated');

-- Seed from gsheet transmission_dict (gid=532607061)
INSERT INTO public.transmission_types (id, name) VALUES
    (1, 'Manualna'),
    (2, 'Automatyczna');
