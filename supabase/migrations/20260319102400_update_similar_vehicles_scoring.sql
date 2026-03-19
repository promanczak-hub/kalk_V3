CREATE OR REPLACE FUNCTION public.rpc_get_similar_vehicles(p_vehicle_id uuid, p_limit integer DEFAULT 5, p_duration_months integer DEFAULT NULL::integer, p_annual_mileage integer DEFAULT NULL::integer)
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, samar_category text, fuel text, transmission text, best_monthly_price numeric, image_url text, similarity_score_pct numeric, suggested_discount_pct numeric)
 LANGUAGE sql
AS $$
    SELECT * FROM reverse_search.rpc_get_similar_vehicles(
        p_vehicle_id, 
        p_limit, 
        p_duration_months, 
        p_annual_mileage
    );
$$;

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_similar_vehicles(p_vehicle_id uuid, p_limit integer DEFAULT 5, p_duration_months integer DEFAULT NULL::integer, p_annual_mileage integer DEFAULT NULL::integer)
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, samar_category text, fuel text, transmission text, best_monthly_price numeric, image_url text, similarity_score_pct numeric, suggested_discount_pct numeric)
 LANGUAGE plpgsql
AS $$
DECLARE
    v_ref record;
BEGIN
    -- 1. Load reference vehicle parameters
    SELECT
        vs.id,
        (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS samar_category,
        (vs.synthesis_data->'mapped_ai_data'->>'engine_class')::text AS engine_class,
        (vs.synthesis_data->'mapped_ai_data'->>'fuel')::text AS fuel,
        (vs.synthesis_data->'mapped_ai_data'->>'transmission')::text AS transmission,
        (vs.synthesis_data->'mapped_ai_data'->>'drive_type')::text AS drive_type,
        (vs.synthesis_data->'mapped_ai_data'->>'body_style')::text AS body_style,
        COALESCE(
            (vs.synthesis_data->'card_summary'->>'base_price')::numeric,
            (vs.synthesis_data->'card_summary'->'parsed_prices'->>'base')::numeric,
            (vs.synthesis_data->'universal_features'->>'cena_pojazdu')::numeric,
            0
        ) AS base_price_gross
    INTO v_ref
    FROM public.vehicle_synthesis vs
    WHERE vs.id = p_vehicle_id;

    -- Safety check: If vehicle not found, or it lacks a base price, we can't do price filtering
    IF v_ref.id IS NULL OR v_ref.base_price_gross = 0 THEN
        RETURN;
    END IF;

    -- 2. Find similar vehicles using weighted multidimensional scoring
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
            (vs.synthesis_data->>'trim_level')::text AS version,
            (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS v_samar,
            (vs.synthesis_data->'mapped_ai_data'->>'fuel')::text AS v_fuel,
            (vs.synthesis_data->'mapped_ai_data'->>'transmission')::text AS v_transmission,
            (vs.synthesis_data->'mapped_ai_data'->>'drive_type')::text AS v_drive,
            (vs.synthesis_data->'mapped_ai_data'->>'body_style')::text AS v_body,
            (vs.synthesis_data->>'image_url')::text AS v_image,
            (vs.synthesis_data->'card_summary'->>'suggested_discount_pct')::numeric AS v_discount,
            COALESCE(
                (vs.synthesis_data->'card_summary'->>'base_price')::numeric,
                (vs.synthesis_data->'card_summary'->'parsed_prices'->>'base')::numeric,
                (vs.synthesis_data->'universal_features'->>'cena_pojazdu')::numeric,
                0
            ) AS v_price,
            
            -- SCORING LOGIC (Max 100 base relevance points)
            -- 1. Price score: max 30 points. Linearly drops to 0 at 25% difference.
            GREATEST(0, 30.0 - (ABS(
                COALESCE(
                    (vs.synthesis_data->'card_summary'->>'base_price')::numeric,
                    (vs.synthesis_data->'card_summary'->'parsed_prices'->>'base')::numeric,
                    (vs.synthesis_data->'universal_features'->>'cena_pojazdu')::numeric,
                    0
                ) - v_ref.base_price_gross
            ) / v_ref.base_price_gross * 100.0) * (30.0 / 25.0)) AS score_price,
            
            -- 2. Body style: 20 points
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'body_style') = v_ref.body_style THEN 20 ELSE 0 END AS score_body,
            
            -- 3. Fuel: 15 points
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'fuel') = v_ref.fuel THEN 15 ELSE 0 END AS score_fuel,
            
            -- 4. Transmission: 15 points
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'transmission') = v_ref.transmission THEN 15 ELSE 0 END AS score_trans,
            
            -- 5. Drive type: 10 points
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'drive_type') = v_ref.drive_type THEN 10 ELSE 0 END AS score_drive,
            
            -- 6. SAMAR Category bonus: 10 points
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'samar_category') = v_ref.samar_category THEN 10 ELSE 0 END AS score_samar

        FROM public.vehicle_synthesis vs
        WHERE vs.id != p_vehicle_id
          AND vs.verification_status = 'completed'
    ),
    filtered_candidates AS (
        SELECT *,
               (score_price + score_body + score_fuel + score_trans + score_drive + score_samar) AS base_relevance
        FROM candidates
        WHERE v_price BETWEEN v_ref.base_price_gross * 0.75 AND v_ref.base_price_gross * 1.25
          AND score_body = 20 -- HARD FILTER FOR BODY STYLE
    ),
    shared_features AS (
        SELECT vfs.source_vehicle_id AS v_id,
               COUNT(*) AS shared
        FROM reverse_search.vehicle_features_summary_view vfs
        JOIN ref_features rf
          ON rf.feature_key = vfs.feature_key
         AND rf.resolved_value_text = vfs.resolved_value_text
        WHERE vfs.source_vehicle_id IN (SELECT v_id FROM filtered_candidates)
        GROUP BY vfs.source_vehicle_id
    ),
    best_prices AS (
        SELECT c.v_id,
               COALESCE(
                   (SELECT MIN(monthly_price_net) FROM public.vehicle_matrix_cache vmc WHERE vmc.vehicle_id = c.v_id AND p_duration_months IS NOT NULL AND p_annual_mileage IS NOT NULL AND vmc.duration_months = p_duration_months AND vmc.annual_mileage = p_annual_mileage),
                   (SELECT MIN(monthly_price_net) FROM public.vehicle_matrix_cache vmc WHERE vmc.vehicle_id = c.v_id)
               ) AS min_price
        FROM filtered_candidates c
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
        -- Final similarity score: blend of hard attributes (80%) and shared standard equipment (20%)
        LEAST(100.0, ROUND(
            (c.base_relevance * 0.8) + 
            ((COALESCE(sf.shared, 0)::numeric / (SELECT total FROM ref_count)) * 100 * 0.2),
            1
        )) AS similarity_score_pct,
        c.v_discount
    FROM filtered_candidates c
    JOIN best_prices bp ON bp.v_id = c.v_id
    LEFT JOIN shared_features sf ON sf.v_id = c.v_id
    WHERE c.base_relevance >= 30 -- Minimum relevance threshold (must have at least matching body + some other factor)
    ORDER BY
        similarity_score_pct DESC,
        CASE WHEN bp.min_price IS NULL THEN 1 ELSE 0 END ASC,
        bp.min_price ASC NULLS LAST
    LIMIT p_limit;
END;
$$;
