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
  -- We extract these carefully from the card_summary object inside the JSONB
  (synthesis_data->'card_summary'->>'powertrain')::TEXT AS powertrain,
  (synthesis_data->'card_summary'->>'transmission')::TEXT AS transmission,
  (synthesis_data->'card_summary'->>'fuel')::TEXT AS fuel,
  (synthesis_data->'card_summary'->>'body_style')::TEXT AS body_style,
  (synthesis_data->'card_summary'->>'trim_level')::TEXT AS trim_level,
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

-- Grants for the view
GRANT ALL ON TABLE public.fleet_management_view TO anon, authenticated;
