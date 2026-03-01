-- Create the storage bucket for PDF uploads if it doesn't exist
INSERT INTO storage.buckets (id, name, public) 
VALUES ('raw-vehicle-pdfs', 'raw-vehicle-pdfs', true) 
ON CONFLICT (id) DO NOTHING;

-- Create policy to allow public reads from the bucket
CREATE POLICY "Public Access" ON storage.objects FOR SELECT USING (bucket_id = 'raw-vehicle-pdfs');

-- Create policy to allow public inserts to the bucket
CREATE POLICY "Public Insert" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'raw-vehicle-pdfs');

-- Create the main vehicle synthesis table
CREATE TABLE IF NOT EXISTS public.vehicle_synthesis (
    id UUID PRIMARY KEY,
    brand TEXT,
    model TEXT,
    offer_number TEXT,
    raw_pdf_url TEXT,
    schema_version TEXT,
    verification_status TEXT,
    synthesis_data JSONB,
    file_hash TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Drop the view if it exists, then recreate it based on the schema and JSON structure
DROP VIEW IF EXISTS public.fleet_management_view;

CREATE OR REPLACE VIEW public.fleet_management_view AS 
SELECT 
  id,
  brand,
  model,
  offer_number,
  raw_pdf_url,
  file_hash,
  notes,
  (synthesis_data->>'configuration_code')::TEXT AS configuration_code,
  (synthesis_data->'card_summary'->>'powertrain')::TEXT AS powertrain,
  (synthesis_data->'card_summary'->>'base_price')::TEXT AS base_price,
  (synthesis_data->'card_summary'->>'options_price')::TEXT AS options_price,
  (synthesis_data->'card_summary'->>'total_price')::TEXT AS final_price_pln,
  (synthesis_data->'card_summary'->>'wheels')::TEXT AS wheels,
  (synthesis_data->'card_summary'->>'emissions')::TEXT AS emissions,
  (synthesis_data->'card_summary'->>'exterior_color')::TEXT AS exterior_color,
  (synthesis_data->'card_summary'->'express_discount_match') AS express_discount_match,
  (synthesis_data->'card_summary'->'standard_equipment') AS standard_equipment,
  (synthesis_data->'card_summary'->'paid_options') AS paid_options,
  synthesis_data,
  created_at
FROM public.vehicle_synthesis;

-- Grants for the table and view
GRANT ALL ON TABLE public.vehicle_synthesis TO anon, authenticated;
GRANT ALL ON TABLE public.fleet_management_view TO anon, authenticated;

-- Disable RLS (or you could create policies, but for internal app we just want it accessible via API endpoint)
ALTER TABLE public.vehicle_synthesis DISABLE ROW LEVEL SECURITY;
