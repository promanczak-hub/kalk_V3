-- Migration: create body_types dictionary table
-- Replaces hardcoded dropdown in VehicleDataSection.tsx

CREATE TABLE public.body_types (
    id serial PRIMARY KEY,
    name text NOT NULL UNIQUE,
    vehicle_class text NOT NULL,
    description text
);

ALTER TABLE public.body_types ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all users"
    ON public.body_types FOR SELECT USING (true);

CREATE POLICY "Enable all access for authenticated users"
    ON public.body_types FOR ALL USING (auth.role() = 'authenticated');

-- Seed with existing values (from VehicleDataSection + extractor_models prompts)
INSERT INTO public.body_types (name, vehicle_class) VALUES
    ('Hatchback', 'Osobowy'),
    ('Kombi', 'Osobowy'),
    ('Sedan', 'Osobowy'),
    ('SUV', 'Osobowy'),
    ('Liftback', 'Osobowy'),
    ('Coupe', 'Osobowy'),
    ('Cabrio', 'Osobowy'),
    ('Minivan', 'Osobowy'),
    ('5 drzwiowy', 'Osobowy'),
    ('4 drzwiowy', 'Osobowy'),
    ('Furgon', 'Dostawczy'),
    ('Pickup', 'Dostawczy'),
    ('Van', 'Dostawczy'),
    ('Podwozie', 'Dostawczy'),
    ('Wieloosobowy', 'Dostawczy'),
    ('Dwuosobowy', 'Dostawczy'),
    ('5 drzwiowy VAN', 'Dostawczy');
