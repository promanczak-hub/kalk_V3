-- Pass paid_options + service_equipment + price_domain through similarity_reasons
-- so the backend Python layer can reuse _extract_option_line_items() to build
-- the same Cena bazowa / Opcje fabryczne / Opcje serwisowe breakdown the source
-- card already shows. Without this passthrough the panel could only show a
-- single-line "Cena kat." (catalog base price) — no options, no totals.
--
-- Builds on 20260505170000 (pricing context fields). Other behaviour unchanged.

CREATE OR REPLACE FUNCTION public.rpc_get_similar_vehicles_batch_semantic(
    p_vehicle_ids uuid[],
    p_limit integer DEFAULT 4,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer,
    p_requirements jsonb DEFAULT '[]'::jsonb
)
 RETURNS SETOF jsonb
 LANGUAGE plpgsql
AS $function$
BEGIN
  RETURN QUERY
  WITH source_setup AS (
    SELECT DISTINCT ON (vmc.vehicle_id)
      vmc.vehicle_id AS source_id,
      vmc.tire_class AS source_tire,
      vmc.service_type AS source_service
    FROM vehicle_matrix_cache vmc
    WHERE vmc.vehicle_id = ANY(p_vehicle_ids)
      AND (p_duration_months IS NULL OR vmc.duration_months = p_duration_months)
      AND (p_annual_mileage IS NULL OR vmc.annual_mileage = p_annual_mileage)
    ORDER BY vmc.vehicle_id, vmc.monthly_price_net ASC, vmc.calculated_at DESC
  ),
  source_embeddings AS (
    SELECT
        vs.id as source_id,
        vs.brand as ref_brand,
        vs.semantic_embedding as source_vec,
        (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS ref_samar,
        (vs.synthesis_data->'mapped_ai_data'->>'fuel')::text AS ref_fuel,
        (vs.synthesis_data->'mapped_ai_data'->>'drive_type')::text AS ref_drive,
        COALESCE(
            (vs.synthesis_data->'mapped_ai_data'->>'body_style')::text,
            (vs.synthesis_data->'card_summary'->>'body_style')::text,
            (vs.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
        ) AS ref_body,
        COALESCE(
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            0
        ) AS ref_price,
        COALESCE(
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'discount'->>'computed_pct', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'suggested_discount_pct', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'offer_discount_pct', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric
        ) AS ref_discount_pct,
        ss.source_tire,
        ss.source_service
    FROM vehicle_synthesis vs
    LEFT JOIN source_setup ss ON ss.source_id = vs.id
    WHERE vs.id = ANY(p_vehicle_ids)
      AND vs.semantic_embedding IS NOT NULL
  ),
  similar_candidates AS (
    SELECT
      se.source_id,
      se.ref_brand,
      se.ref_samar, se.ref_fuel, se.ref_drive, se.ref_body, se.ref_price, se.ref_discount_pct,
      se.source_tire, se.source_service,
      v.id as v_id,
      v.brand,
      v.model,
      ROUND(((1 - (v.semantic_embedding <=> se.source_vec)) * 100)::numeric, 2) as score,
      v.synthesis_data,
      (v.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS cand_samar,
      (v.synthesis_data->'mapped_ai_data'->>'fuel')::text AS cand_fuel,
      (v.synthesis_data->'mapped_ai_data'->>'drive_type')::text AS cand_drive,
      COALESCE(
        (v.synthesis_data->'mapped_ai_data'->>'body_style')::text,
        (v.synthesis_data->'card_summary'->>'body_style')::text,
        (v.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
      ) AS cand_body,
      COALESCE(
        NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
        NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
        NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
        0
      ) AS cand_price,
      COALESCE(
        NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->'discount'->>'computed_pct', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
        NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->>'suggested_discount_pct', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
        NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->>'offer_discount_pct', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric
      ) AS cand_discount_pct,
      ROW_NUMBER() OVER(PARTITION BY se.source_id ORDER BY v.semantic_embedding <=> se.source_vec) as rank
    FROM source_embeddings se
    CROSS JOIN vehicle_synthesis v
    WHERE v.id != se.source_id
    AND v.semantic_embedding IS NOT NULL
    AND v.verification_status = 'completed'
    AND (
        public.fn_class_super(se.ref_samar) IS NULL
        OR public.fn_class_super(se.ref_samar) =
           public.fn_class_super(
               (v.synthesis_data->'mapped_ai_data'->>'samar_category')::text
           )
    )
    AND (
        public.fn_body_family(se.ref_body) IS NULL
        OR public.fn_body_family(se.ref_body) =
           public.fn_body_family(
               COALESCE(
                   (v.synthesis_data->'mapped_ai_data'->>'body_style')::text,
                   (v.synthesis_data->'card_summary'->>'body_style')::text,
                   (v.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
               )
           )
    )
    AND (
        jsonb_array_length(COALESCE(p_requirements, '[]'::jsonb)) = 0
        OR NOT EXISTS (
            SELECT 1 FROM jsonb_array_elements(p_requirements) req
            LEFT JOIN reverse_search.vehicle_features_summary_view vfs
                   ON vfs.source_vehicle_id = v.id
                  AND vfs.feature_key = req->>'feature_key'
            WHERE req->>'requirement' = 'MUST_HAVE'
              AND req->>'feature_key' NOT IN ('monthly_price_net', 'duration_months', 'annual_mileage', 'margin_pct', 'dummy')
              AND NOT (
                   (req->>'feature_key' like 'opt_std:%' AND coalesce(v.synthesis_data->'card_summary'->'standard_equipment', '[]'::jsonb) @> jsonb_build_array(substring(req->>'feature_key' from 9))) OR
                   (req->>'feature_key' like 'opt_paid:%' AND coalesce(v.synthesis_data->'card_summary'->'paid_options', '[]'::jsonb) @> jsonb_build_array(jsonb_build_object('name', substring(req->>'feature_key' from 10)))) OR
                   (req->>'feature_key' = 'body_style' AND coalesce((v.synthesis_data->'mapped_ai_data'->>'body_style')::text, (v.synthesis_data->'card_summary'->>'body_style')::text, (v.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text) = req->>'value') OR
                   (req->>'operator' = 'eq' and req->>'value' = 'true' and vfs.resolved_value_bool = true) OR
                   (req->>'operator' = 'eq' and req->>'value' = 'false' and coalesce(vfs.resolved_value_bool, false) = false) OR
                   (req->>'operator' = 'eq' and vfs.resolved_value_text = req->>'value') OR
                   (req->>'operator' = 'gte' and vfs.resolved_value_num >= (req->>'value')::numeric) OR
                   (req->>'operator' = 'lte' and vfs.resolved_value_num <= (req->>'value')::numeric) OR
                   (req->>'operator' = 'in' and (req->'values') @> to_jsonb(vfs.resolved_value_text))
              )
        )
    )
  ),
  candidate_match AS (
    SELECT DISTINCT ON (c.source_id, c.v_id)
      c.source_id,
      c.v_id,
      mc.monthly_price_net,
      mc.kalkulacja_id,
      mc.tire_class AS matched_tire,
      mc.service_type AS matched_service
    FROM similar_candidates c
    LEFT JOIN vehicle_matrix_cache mc
      ON mc.vehicle_id = c.v_id
     AND (p_duration_months IS NULL OR mc.duration_months = p_duration_months)
     AND (p_annual_mileage IS NULL OR mc.annual_mileage = p_annual_mileage)
     AND mc.tire_class IS NOT DISTINCT FROM c.source_tire
     AND mc.service_type IS NOT DISTINCT FROM c.source_service
    WHERE c.rank <= p_limit
    ORDER BY c.source_id, c.v_id, mc.calculated_at DESC NULLS LAST
  )
  SELECT
    jsonb_build_object(
      'source_vehicle_id', c.source_id,
      'vehicle_id', c.v_id,
      'brand', c.brand,
      'model', c.model,
      'version', COALESCE(c.synthesis_data->'card_summary'->>'trim_level', ''),
      'samar_category', COALESCE(c.synthesis_data->'card_summary'->>'samar_category', 'N/A'),
      'fuel', COALESCE(c.synthesis_data->'card_summary'->>'powertrain', 'N/A'),
      'transmission', COALESCE(c.synthesis_data->'card_summary'->>'transmission', 'N/A'),
      'body_style', COALESCE(c.cand_body, c.synthesis_data->'card_summary'->>'body_style', 'N/A'),
      'drive_type', COALESCE(c.synthesis_data->'card_summary'->>'drivetrain', 'N/A'),
      'vehicle_class', COALESCE(c.cand_samar, c.synthesis_data->'card_summary'->>'samar_category', 'N/A'),
      'image_url', COALESCE(c.synthesis_data->'card_summary'->>'image_url', ''),
      'similarity_score_pct', c.score,
      'similarity_reasons', jsonb_build_object(
          'samar_match',     (c.cand_samar = c.ref_samar AND c.ref_samar IS NOT NULL),
          'body_match',      (c.cand_body = c.ref_body AND c.ref_body IS NOT NULL),
          'fuel_match',      (c.cand_fuel = c.ref_fuel AND c.ref_fuel IS NOT NULL),
          'drive_match',     (c.cand_drive = c.ref_drive AND c.ref_drive IS NOT NULL),
          'equipment_match', (c.score > 75),
          'equipment_similarity_pct', c.score,
          'is_same_brand',   (c.brand = c.ref_brand AND c.ref_brand IS NOT NULL),
          'price_pct_diff',  ROUND(ABS(c.cand_price - c.ref_price) / GREATEST(c.ref_price, 1) * 100, 1),
          'samar_category',  COALESCE(c.cand_samar, 'N/A'),
          'body_style',      COALESCE(c.cand_body, 'N/A'),
          'setup_match',     (cm.monthly_price_net IS NOT NULL),
          'source_tire_class',  c.source_tire,
          'source_service_type', c.source_service,
          'base_price',                c.cand_price,
          'discount_pct',              c.cand_discount_pct,
          'discount_pct_diff',         CASE
                                          WHEN c.cand_discount_pct IS NOT NULL
                                           AND c.ref_discount_pct  IS NOT NULL
                                          THEN ROUND(c.cand_discount_pct - c.ref_discount_pct, 1)
                                          ELSE NULL
                                       END,
          'matched_duration_months',   p_duration_months,
          'matched_annual_mileage',    p_annual_mileage,
          -- Raw passthrough for backend Python to split into factory/service.
          'paid_options',              c.synthesis_data->'card_summary'->'paid_options',
          'service_equipment',         c.synthesis_data->'card_summary'->'service_equipment',
          'price_domain',              c.synthesis_data->'card_summary'->>'price_domain'
      ),
      'best_monthly_price', cm.monthly_price_net,
      'kalkulacja_id', cm.kalkulacja_id
    )
  FROM similar_candidates c
  LEFT JOIN candidate_match cm ON cm.source_id = c.source_id AND cm.v_id = c.v_id
  WHERE c.rank <= p_limit;
END;
$function$;
