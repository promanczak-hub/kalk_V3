-- Fix: Add COALESCE fallback to mapped_ai_data for key vehicle fields
-- This ensures data is shown even when card_summary extraction fails

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
  verification_status,
  (synthesis_data->>'configuration_code')::TEXT AS configuration_code,

  -- Technical fields: card_summary first, mapped_ai_data as fallback
  COALESCE(
    synthesis_data->'card_summary'->>'powertrain',
    synthesis_data->'mapped_ai_data'->>'powertrain'
  )::TEXT AS powertrain,

  COALESCE(
    synthesis_data->'card_summary'->>'fuel',
    synthesis_data->'mapped_ai_data'->>'fuel'
  )::TEXT AS fuel,

  COALESCE(
    synthesis_data->'card_summary'->>'transmission',
    synthesis_data->'mapped_ai_data'->>'transmission'
  )::TEXT AS transmission,

  COALESCE(
    synthesis_data->'card_summary'->>'trim_level',
    synthesis_data->'mapped_ai_data'->>'trim_level'
  )::TEXT AS trim_level,

  (synthesis_data->'card_summary'->>'base_price')::TEXT AS base_price,
  (synthesis_data->'card_summary'->>'options_price')::TEXT AS options_price,
  (synthesis_data->'card_summary'->>'total_price')::TEXT AS final_price_pln,
  (synthesis_data->'card_summary'->>'wheels')::TEXT AS wheels,
  (synthesis_data->'card_summary'->>'emissions')::TEXT AS emissions,
  (synthesis_data->'card_summary'->>'exterior_color')::TEXT AS exterior_color,
  (synthesis_data->'card_summary'->>'body_style')::TEXT AS body_style,
  (synthesis_data->'card_summary'->'express_discount_match') AS express_discount_match,
  (synthesis_data->'card_summary'->>'suggested_discount_pct')::NUMERIC AS suggested_discount_pct,
  (synthesis_data->'card_summary'->>'suggested_discount_source')::TEXT AS suggested_discount_source,
  (synthesis_data->'card_summary'->'standard_equipment') AS standard_equipment,
  (synthesis_data->'card_summary'->'paid_options') AS paid_options,
  synthesis_data,
  created_at
FROM public.vehicle_synthesis;

GRANT ALL ON TABLE public.fleet_management_view TO anon, authenticated;
