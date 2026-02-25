CREATE TABLE public.control_center (
    id integer PRIMARY KEY CHECK (id = 1),
    default_wibor numeric(5,2) NOT NULL DEFAULT 5.85,
    default_ltr_margin numeric(5,2) NOT NULL DEFAULT 15.00,
    bank_spread numeric(5,2) NOT NULL DEFAULT 1.50,
    samar_segment_b_adjustment integer NOT NULL DEFAULT -1,
    samar_segment_c_adjustment integer NOT NULL DEFAULT -1,
    samar_segment_d_adjustment integer NOT NULL DEFAULT 0,
    value_threshold_1 numeric(12,2) NOT NULL DEFAULT 140000.00,
    value_threshold_2 numeric(12,2) NOT NULL DEFAULT 190000.00,
    resale_time_days integer NOT NULL DEFAULT 45,
    inventory_financing_cost numeric(5,2) NOT NULL DEFAULT 1.50,
    updated_at timestamp with time zone DEFAULT now()
);

-- Insert the default singleton row
INSERT INTO public.control_center (
    id, 
    default_wibor, 
    default_ltr_margin, 
    bank_spread, 
    samar_segment_b_adjustment, 
    samar_segment_c_adjustment, 
    samar_segment_d_adjustment, 
    value_threshold_1, 
    value_threshold_2, 
    resale_time_days, 
    inventory_financing_cost
) VALUES (
    1, 
    5.85, 
    15.00, 
    1.50, 
    -1, 
    -1, 
    0, 
    140000.00, 
    190000.00, 
    45, 
    1.50
);

-- Add updated_at trigger
CREATE OR REPLACE FUNCTION update_control_center_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_control_center_updated_at
BEFORE UPDATE ON public.control_center
FOR EACH ROW
EXECUTE FUNCTION update_control_center_updated_at();

-- Set up RLS to allow reading and updating
ALTER TABLE public.control_center ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access for control_center" 
ON public.control_center 
FOR SELECT 
USING (true);

-- Allow anon updates for simplicity in this MVP (or service role)
-- The UI might need to save parameters anonymously
CREATE POLICY "Allow public update access for control_center" 
ON public.control_center 
FOR UPDATE 
USING (true)
WITH CHECK (true);
