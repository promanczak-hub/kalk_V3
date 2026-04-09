-- Migration to add p_requirements support to rpc_get_alternatives_semantic

DROP FUNCTION IF EXISTS public.rpc_get_alternatives_semantic(uuid, vector, integer, integer, integer);
DROP FUNCTION IF EXISTS reverse_search.rpc_get_alternatives_semantic(uuid, vector, integer, integer, integer);

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_alternatives_semantic(
    p_vehicle_id uuid,
    p_synthetic_vector vector(768),
    p_limit integer DEFAULT 5,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer,
    p_requirements jsonb DEFAULT '[]'::jsonb
)
 RETURNS TABLE(similarity_json jsonb)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
DECLARE
    v_ref record;
    v_has_must_have boolean;
BEGIN
    -- Base vehicle data to find the current samar_category
    SELECT
        (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS samar_category
    INTO v_ref
    FROM public.vehicle_synthesis vs
    WHERE vs.id = p_vehicle_id;

    IF v_ref.samar_category IS NULL THEN
        RETURN;
    END IF;

    -- Check if we have MUST_HAVE requirements to bother filtering
    SELECT EXISTS (
        SELECT 1 FROM jsonb_array_elements(
            CASE WHEN jsonb_array_length(COALESCE(p_requirements, '[]'::jsonb)) > 0 
                 THEN p_requirements 
                 ELSE '[{"feature_key": "dummy", "requirement": "dummy"}]'::jsonb 
            END
        ) AS req
        WHERE req->>'requirement' = 'MUST_HAVE'
    ) INTO v_has_must_have;

    RETURN QUERY
    WITH target_vehicles AS (
        SELECT v.id as v_id,
               v.brand,
               v.model,
               v.semantic_embedding,
               v.synthesis_data
        FROM public.vehicle_synthesis v
        WHERE v.id != p_vehicle_id
          AND v.semantic_embedding IS NOT NULL
          AND (v.synthesis_data->'mapped_ai_data'->>'samar_category')::text = v_ref.samar_category
          AND v.verification_status = 'completed'
    ),
    vehicle_evals AS (
        SELECT tv.v_id,
               req->>'feature_key' AS feature_key,
               req->>'requirement' AS requirement,
               vfs.resolved_value_bool,
               vfs.resolved_value_num,
               vfs.resolved_value_text,
               CASE 
                   WHEN req->>'feature_key' = 'dummy' THEN true
                   WHEN req->>'feature_key' IN ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net') THEN true
                   WHEN req->>'feature_key' LIKE 'opt_std:%' THEN
                       (COALESCE(tv.synthesis_data->'card_summary'->'standard_equipment', '[]'::jsonb) @> jsonb_build_array(substring(req->>'feature_key' from 9)))
                   WHEN req->>'feature_key' LIKE 'opt_paid:%' THEN
                       (COALESCE(tv.synthesis_data->'card_summary'->'paid_options', '[]'::jsonb) @> jsonb_build_array(jsonb_build_object('name', substring(req->>'feature_key' from 10))))
                   WHEN req->>'operator' = 'eq' AND req->>'value' = 'true' AND vfs.resolved_value_bool = true THEN true
                   WHEN req->>'operator' = 'eq' AND req->>'value' = 'false' AND (COALESCE(vfs.resolved_value_bool, false) = false) THEN true
                   WHEN req->>'operator' = 'eq' AND vfs.resolved_value_text = req->>'value' THEN true
                   WHEN req->>'operator' = 'gte' AND vfs.resolved_value_num >= (req->>'value')::numeric THEN true
                   WHEN req->>'operator' = 'lte' AND vfs.resolved_value_num <= (req->>'value')::numeric THEN true
                   WHEN req->>'operator' = 'in' AND (req->'values') @> to_jsonb(vfs.resolved_value_text) THEN true
                   ELSE false
               END AS is_match
        FROM target_vehicles tv
        LEFT JOIN jsonb_array_elements(
            CASE WHEN jsonb_array_length(COALESCE(p_requirements, '[]'::jsonb)) > 0 
                 THEN p_requirements 
                 ELSE '[{"feature_key": "dummy", "requirement": "dummy"}]'::jsonb 
            END
        ) AS req ON true
        LEFT JOIN reverse_search.vehicle_features_summary_view vfs 
               ON vfs.source_vehicle_id = tv.v_id 
              AND vfs.feature_key = req->>'feature_key'
    ),
    failed_must_haves AS (
        SELECT DISTINCT v_id
        FROM vehicle_evals
        WHERE requirement = 'MUST_HAVE' AND is_match = false
    )
    SELECT 
        jsonb_build_object(
            'vehicle_id', tv.v_id,
            'brand', tv.brand,
            'model', tv.model,
            'version', COALESCE(tv.synthesis_data->'card_summary'->>'trim_level', ''),
            'samar_category', COALESCE(tv.synthesis_data->'mapped_ai_data'->>'samar_category', 'N/A'),
            'fuel', COALESCE(tv.synthesis_data->'mapped_ai_data'->>'fuel', 'N/A'),
            'transmission', COALESCE(tv.synthesis_data->'mapped_ai_data'->>'transmission', 'N/A'),
            'image_url', COALESCE(tv.synthesis_data->>'image_url', ''),
            'power_hp', COALESCE((tv.synthesis_data->'card_summary'->>'power_hp')::integer, (tv.synthesis_data->'universal_features'->>'Moc silnika (KM)')::integer, 0),
            'similarity_score_pct', ROUND(((1 - (tv.semantic_embedding <=> p_synthetic_vector)) * 100)::numeric, 2),
            'best_monthly_price', (
                SELECT MIN(monthly_price_net)
                FROM public.vehicle_matrix_cache mc
                WHERE mc.vehicle_id = tv.v_id
                AND (p_duration_months IS NULL OR mc.duration_months = p_duration_months)
                AND (p_annual_mileage IS NULL OR mc.annual_mileage = p_annual_mileage)
            ),
            'similarity_reasons', jsonb_build_object(
                 'base_price', COALESCE(
                                    NULLIF(REGEXP_REPLACE(REPLACE(tv.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                                    NULLIF(REGEXP_REPLACE(REPLACE(tv.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                                    NULLIF(REGEXP_REPLACE(REPLACE(tv.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                                    0
                               ),
                 'paid_options', (tv.synthesis_data->'card_summary'->'paid_options')
            )
        )
    FROM target_vehicles tv
    WHERE tv.v_id NOT IN (SELECT v_id FROM failed_must_haves)
    ORDER BY tv.semantic_embedding <=> p_synthetic_vector
    LIMIT p_limit;
END;
$function$;

CREATE OR REPLACE FUNCTION public.rpc_get_alternatives_semantic(
    p_vehicle_id uuid,
    p_synthetic_vector vector(768),
    p_limit integer DEFAULT 5,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer,
    p_requirements jsonb DEFAULT '[]'::jsonb
)
 RETURNS TABLE(similarity_json jsonb)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
BEGIN
    RETURN QUERY 
    SELECT * FROM reverse_search.rpc_get_alternatives_semantic(
        p_vehicle_id, 
        p_synthetic_vector, 
        p_limit, 
        p_duration_months, 
        p_annual_mileage,
        p_requirements
    );
END;
$function$;
