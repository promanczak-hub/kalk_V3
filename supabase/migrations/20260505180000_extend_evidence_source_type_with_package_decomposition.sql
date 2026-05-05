-- Allow 'package_decomposition' as a valid source_type for vehicle_feature_evidence.
-- The enrichment pipeline (core/feature_enrichment.py) writes this value when an
-- LLM decomposes a paid package (e.g. "Driver Assistance Pack 11") into its
-- constituent boolean features. The CHECK constraint was missing this case, so
-- those evidence rows were rejected (PG error 23514) and the entire enrichment
-- batch failed for any vehicle whose card_summary contained packages.

ALTER TABLE reverse_search.vehicle_feature_evidence
  DROP CONSTRAINT IF EXISTS vehicle_feature_evidence_source_type_check;

ALTER TABLE reverse_search.vehicle_feature_evidence
  ADD CONSTRAINT vehicle_feature_evidence_source_type_check
  CHECK (source_type = ANY (ARRAY[
    'spec'::text,
    'variant_doc'::text,
    'catalog'::text,
    'brochure'::text,
    'price_list'::text,
    'excel_import'::text,
    'service_option'::text,
    'body_parameters'::text,
    'manual_override'::text,
    'llm_inference'::text,
    'package_decomposition'::text
  ]));
