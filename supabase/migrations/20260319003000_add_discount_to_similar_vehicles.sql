CREATE OR REPLACE FUNCTION public.rpc_get_similar_vehicles(p_vehicle_id uuid, p_limit integer DEFAULT 5, p_duration_months integer DEFAULT NULL::integer, p_annual_mileage integer DEFAULT NULL::integer)
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, samar_category text, fuel text, transmission text, best_monthly_price numeric, image_url text, similarity_score_pct numeric, suggested_discount_pct numeric)
 LANGUAGE sql
AS $function$
    SELECT * FROM reverse_search.rpc_get_similar_vehicles(
        p_vehicle_id, 
        p_limit, 
        p_duration_months, 
        p_annual_mileage
    );
$function$;

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_similar_vehicles(p_vehicle_id uuid, p_limit integer DEFAULT 5, p_duration_months integer DEFAULT NULL::integer, p_annual_mileage integer DEFAULT NULL::integer)
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, samar_category text, fuel text, transmission text, best_monthly_price numeric, image_url text, similarity_score_pct numeric, suggested_discount_pct numeric)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_samar_category text;
    v_samar_prefix   text;
    v_engine_class   text;
    v_fuel           text;
BEGIN
    -- 1. Load reference vehicle parameters
    SELECT
        vs.synthesis_data->'mapped_ai_data'->>'samar_category',
        vs.synthesis_data->'mapped_ai_data'->>'engine_class',
        vs.synthesis_data->'mapped_ai_data'->>'fuel'
    INTO v_samar_category, v_engine_class, v_fuel
    FROM public.vehicle_synthesis vs
    WHERE vs.id = p_vehicle_id;

    IF v_samar_category IS NULL THEN
        RETURN;
    END IF;

    -- Extract SAMAR "family" prefix: everything before the dash (e.g. "Terenowo-rekreacyjne (SUV)")
    v_samar_prefix := TRIM(SPLIT_PART(v_samar_category, '-', 1));

    -- 2. Find similar vehicles
    RETURN QUERY
    WITH ref_features AS (
        SELECT feature_key, resolved_value_text
        FROM reverse_search.vehicle_features_summary_view
        WHERE source_vehicle_id = p_vehicle_id
    ),
    ref_count AS (
        SELECT GREATEST(COUNT(*), 1)::numeric AS total FROM ref_features
    ),
    candidates AS (
        SELECT
            vs.id AS v_id,
            vs.brand,
            vs.model,
            (vs.synthesis_data->>'trim_level')::text                      AS version,
            (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS v_samar,
            (vs.synthesis_data->'mapped_ai_data'->>'fuel')::text           AS v_fuel,
            (vs.synthesis_data->'mapped_ai_data'->>'transmission')::text   AS v_transmission,
            (vs.synthesis_data->>'image_url')::text                        AS v_image,
            (vs.synthesis_data->'card_summary'->>'suggested_discount_pct')::numeric AS v_discount,
            -- Relevance score: 2 = same SAMAR class, 1 = same SAMAR family + same engine class
            CASE
                WHEN vs.synthesis_data->'mapped_ai_data'->>'samar_category' = v_samar_category
                    THEN 2
                WHEN vs.synthesis_data->'mapped_ai_data'->>'samar_category' ILIKE v_samar_prefix || '%'
                 AND vs.synthesis_data->'mapped_ai_data'->>'engine_class' = v_engine_class
                    THEN 1
                ELSE 0
            END AS relevance
        FROM public.vehicle_synthesis vs
        WHERE vs.id != p_vehicle_id
          AND vs.verification_status = 'completed'
          AND (
              vs.synthesis_data->'mapped_ai_data'->>'samar_category' = v_samar_category
              OR (
                  vs.synthesis_data->'mapped_ai_data'->>'samar_category' ILIKE v_samar_prefix || '%'
                  AND vs.synthesis_data->'mapped_ai_data'->>'engine_class' = v_engine_class
              )
          )
    ),
    shared_features AS (
        SELECT vfs.source_vehicle_id AS v_id,
               COUNT(*) AS shared
        FROM reverse_search.vehicle_features_summary_view vfs
        JOIN ref_features rf
          ON rf.feature_key = vfs.feature_key
         AND rf.resolved_value_text = vfs.resolved_value_text
        WHERE vfs.source_vehicle_id IN (SELECT v_id FROM candidates)
        GROUP BY vfs.source_vehicle_id
    ),
    best_prices AS (
        SELECT c.v_id,
               COALESCE(
                   (SELECT MIN(monthly_price_net) FROM public.vehicle_matrix_cache vmc WHERE vmc.vehicle_id = c.v_id AND p_duration_months IS NOT NULL AND p_annual_mileage IS NOT NULL AND vmc.duration_months = p_duration_months AND vmc.annual_mileage = p_annual_mileage),
                   (SELECT MIN(monthly_price_net) FROM public.vehicle_matrix_cache vmc WHERE vmc.vehicle_id = c.v_id)
               ) AS min_price
        FROM candidates c
    )
    SELECT
        c.v_id::uuid,
        c.brand,
        c.model,
        c.version,
        COALESCE(c.v_samar, 'N/A'),
        COALESCE(c.v_fuel, 'N/A'),
        COALESCE(c.v_transmission, 'N/A'),
        bp.min_price,
        c.v_image,
        ROUND(
            (COALESCE(sf.shared, 0)::numeric / (SELECT total FROM ref_count)) * 100,
            1
        ),
        c.v_discount
    FROM candidates c
    JOIN best_prices bp ON bp.v_id = c.v_id
    LEFT JOIN shared_features sf ON sf.v_id = c.v_id
    ORDER BY
        c.relevance DESC,
        CASE WHEN bp.min_price IS NULL THEN 1 ELSE 0 END ASC,
        bp.min_price ASC NULLS LAST,
        COALESCE(sf.shared, 0) DESC
    LIMIT p_limit;
END;
$function$;
