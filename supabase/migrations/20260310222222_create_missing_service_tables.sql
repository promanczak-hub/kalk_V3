-- Migration to create missing service tables:
-- 1. samar_service_costs
-- 2. service_rates_config
-- 3. service_base_costs_config

-- 1. samar_service_costs
CREATE TABLE IF NOT EXISTS public.samar_service_costs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    samar_class_id INT NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    engine_type_id INT NOT NULL REFERENCES public.engines(id) ON DELETE CASCADE,
    power_band TEXT NOT NULL CHECK (power_band IN ('LOW', 'MID', 'HIGH')),
    cost_aso_per_km NUMERIC NOT NULL DEFAULT 0.0,
    cost_non_aso_per_km NUMERIC NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for samar_service_costs
CREATE INDEX IF NOT EXISTS idx_samar_service_costs_samar_class_id ON public.samar_service_costs(samar_class_id);
CREATE INDEX IF NOT EXISTS idx_samar_service_costs_engine_type_id ON public.samar_service_costs(engine_type_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_samar_service_costs_unique ON public.samar_service_costs(samar_class_id, engine_type_id, power_band);

-- RLS for samar_service_costs
ALTER TABLE public.samar_service_costs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow full access to all roles" ON public.samar_service_costs
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- 2. service_rates_config
CREATE TABLE IF NOT EXISTS public.service_rates_config (
    id SERIAL PRIMARY KEY,
    klasa_id INT NOT NULL,
    rodzaj_paliwa TEXT NOT NULL,
    stawka_za_km NUMERIC NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS for service_rates_config
ALTER TABLE public.service_rates_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow full access to all roles" ON public.service_rates_config
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- 3. service_base_costs_config
CREATE TABLE IF NOT EXISTS public.service_base_costs_config (
    id SERIAL PRIMARY KEY,
    klasa_id INT NOT NULL,
    koszt_przegladu_podstawowego NUMERIC NOT NULL DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- RLS for service_base_costs_config
ALTER TABLE public.service_base_costs_config ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Allow full access to all roles" ON public.service_base_costs_config
    FOR ALL
    USING (true)
    WITH CHECK (true);
