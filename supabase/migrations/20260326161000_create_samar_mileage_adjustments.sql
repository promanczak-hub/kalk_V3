-- Create the new table for mileage adjustments
CREATE TABLE IF NOT EXISTS public.samar_mileage_adjustments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    samar_class_id INTEGER NOT NULL REFERENCES public.samar_classes(id) ON DELETE CASCADE,
    max_mileage_target BIGINT NOT NULL,
    correction_below_threshold NUMERIC NOT NULL,
    correction_above_threshold NUMERIC NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Ensure 1:1 relationship between SAMAR class and its adjustments
CREATE UNIQUE INDEX IF NOT EXISTS uq_mileage_adj_samar_class ON public.samar_mileage_adjustments(samar_class_id);

-- Enable RLS
ALTER TABLE public.samar_mileage_adjustments ENABLE ROW LEVEL SECURITY;

-- Grant access
GRANT SELECT, INSERT, UPDATE, DELETE ON public.samar_mileage_adjustments TO authenticated;
GRANT SELECT ON public.samar_mileage_adjustments TO anon;

-- Policies
CREATE POLICY "Enable read access for all users" ON public.samar_mileage_adjustments FOR SELECT USING (true);
CREATE POLICY "Enable all access for authenticated users" ON public.samar_mileage_adjustments FOR ALL TO authenticated USING (true) WITH CHECK (true);
