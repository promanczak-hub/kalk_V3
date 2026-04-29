-- Recreate fleet_management_view to expose the new koszt_dzienny_min column

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
  document_category,
  (synthesis_data->>'configuration_code')::TEXT AS configuration_code,

  COALESCE(
    NULLIF(NULLIF(TRIM(synthesis_data->'card_summary'->>'powertrain'), 'Brak'), ''),
    NULLIF(NULLIF(TRIM(synthesis_data->'mapped_ai_data'->>'powertrain'), 'Brak'), '')
  )::TEXT AS powertrain,

  COALESCE(
    NULLIF(NULLIF(TRIM(synthesis_data->'card_summary'->>'fuel'), 'Brak'), ''),
    NULLIF(NULLIF(TRIM(synthesis_data->'mapped_ai_data'->>'fuel'), 'Brak'), '')
  )::TEXT AS fuel,

  COALESCE(
    NULLIF(NULLIF(TRIM(synthesis_data->'card_summary'->>'transmission'), 'Brak'), ''),
    NULLIF(NULLIF(TRIM(synthesis_data->'mapped_ai_data'->>'transmission'), 'Brak'), '')
  )::TEXT AS transmission,

  COALESCE(
    NULLIF(NULLIF(TRIM(synthesis_data->'card_summary'->>'trim_level'), 'Brak'), ''),
    NULLIF(NULLIF(TRIM(synthesis_data->'mapped_ai_data'->>'trim_level'), 'Brak'), '')
  )::TEXT AS trim_level,

  (synthesis_data->'card_summary'->>'base_price')::TEXT AS base_price,
  (synthesis_data->'card_summary'->>'options_price')::TEXT AS options_price,
  (synthesis_data->'card_summary'->>'total_price')::TEXT AS final_price_pln,
  (synthesis_data->'card_summary'->>'wheels')::TEXT AS wheels,
  (synthesis_data->'card_summary'->>'emissions')::TEXT AS emissions,
  (synthesis_data->'card_summary'->>'exterior_color')::TEXT AS exterior_color,
  (synthesis_data->'card_summary'->>'body_style')::TEXT AS body_style,
  (synthesis_data->'card_summary'->>'vehicle_class')::TEXT AS vehicle_class,

  (synthesis_data->'card_summary'->>'drive_type')::TEXT AS drive_type,
  (synthesis_data->'card_summary'->>'number_of_seats')::INT AS number_of_seats,
  (synthesis_data->'card_summary'->>'is_metalic_paint')::BOOLEAN AS is_metalic_paint,

  (synthesis_data->'card_summary'->'express_discount_match') AS express_discount_match,
  (synthesis_data->'card_summary'->>'suggested_discount_pct')::NUMERIC AS suggested_discount_pct,
  (synthesis_data->'card_summary'->>'suggested_discount_source')::TEXT AS suggested_discount_source,
  (synthesis_data->'card_summary'->>'suggested_discount_confidence')::NUMERIC AS suggested_discount_confidence,
  (synthesis_data->'card_summary'->'standard_equipment') AS standard_equipment,
  (synthesis_data->'card_summary'->'paid_options') AS paid_options,
  synthesis_data,
  koszt_dzienny_min,
  created_at
FROM public.vehicle_synthesis;

GRANT ALL ON TABLE public.fleet_management_view TO anon, authenticated;
