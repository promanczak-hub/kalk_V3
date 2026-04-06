-- Migration: add_alternatives_rpcs.sql

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_alternatives_math(
    p_vehicle_id uuid,
    p_category text,
    p_limit integer DEFAULT 5,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer
)
 RETURNS TABLE(similarity_json jsonb)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
DECLARE
    v_ref record;
BEGIN
    -- Base vehicle data
    SELECT
        vs.id,
        vs.brand,
        (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS samar_category,
        COALESCE(
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            0
        ) AS base_price_gross,
        COALESCE((vs.synthesis_data->'card_summary'->>'power_hp')::integer, (vs.synthesis_data->'universal_features'->>'Moc silnika (KM)')::integer, 0) AS power_hp,
        COALESCE(
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'Średnie spalanie (Katalogowe)', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'Pojemność baterii (kWh)', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'fuel_consumption_mixed', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            0
        ) AS eco_metric
    INTO v_ref
    FROM public.vehicle_synthesis vs
    WHERE vs.id = p_vehicle_id;

    IF v_ref.id IS NULL OR v_ref.samar_category IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    WITH candidates AS (
        SELECT
            vs.id AS v_id,
            vs.brand,
            vs.model,
            (vs.synthesis_data->>'trim_level')::text AS version,
            (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS v_samar,
            (vs.synthesis_data->'mapped_ai_data'->>'fuel')::text AS fuel,
            (vs.synthesis_data->'mapped_ai_data'->>'transmission')::text AS transmission,
            (vs.synthesis_data->>'image_url')::text AS image_url,
            COALESCE((vs.synthesis_data->'card_summary'->>'power_hp')::integer, (vs.synthesis_data->'universal_features'->>'Moc silnika (KM)')::integer, 0) AS v_power,
            COALESCE(
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                0
            ) AS v_price_gross,
            COALESCE(
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'Średnie spalanie (Katalogowe)', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'Pojemność baterii (kWh)', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'fuel_consumption_mixed', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                0
            ) AS v_eco_metric,
            vs.synthesis_data
        FROM public.vehicle_synthesis vs
        WHERE vs.id != p_vehicle_id
          AND vs.verification_status = 'completed'
          AND (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text = v_ref.samar_category
    ),
    best_prices AS (
        SELECT c.v_id,
               COALESCE(
                   (SELECT MIN(monthly_price_net) FROM public.vehicle_matrix_cache vmc WHERE vmc.vehicle_id = c.v_id AND p_duration_months IS NOT NULL AND p_annual_mileage IS NOT NULL AND vmc.duration_months = p_duration_months AND vmc.annual_mileage = p_annual_mileage),
                   (SELECT MIN(monthly_price_net) FROM public.vehicle_matrix_cache vmc WHERE vmc.vehicle_id = c.v_id)
               ) AS min_price
        FROM candidates c
    ),
    filtered_and_scored AS (
        SELECT 
            c.*, 
            bp.min_price,
            CASE 
                WHEN p_category = 'cheaper' THEN (v_ref.base_price_gross - c.v_price_gross) / GREATEST(v_ref.base_price_gross, 1) * 100
                WHEN p_category = 'stronger' THEN (c.v_power - v_ref.power_hp)::numeric / GREATEST(v_ref.power_hp, 1) * 100
                WHEN p_category = 'greener' THEN (v_ref.eco_metric - c.v_eco_metric) / GREATEST(v_ref.eco_metric, 1) * 100
                ELSE 0 
            END AS category_score
        FROM candidates c
        JOIN best_prices bp ON bp.v_id = c.v_id
        WHERE 
            (p_category = 'cheaper' AND c.v_price_gross < v_ref.base_price_gross * 0.95) OR
            (p_category = 'stronger' AND c.v_power > v_ref.power_hp * 1.05) OR
            (p_category = 'greener' AND c.v_eco_metric < v_ref.eco_metric * 0.9 AND c.v_eco_metric > 0)
    )
    SELECT 
        jsonb_build_object(
            'vehicle_id', fs.v_id,
            'brand', fs.brand,
            'model', fs.model,
            'version', fs.version,
            'samar_category', fs.v_samar,
            'fuel', fs.fuel,
            'transmission', fs.transmission,
            'image_url', fs.image_url,
            'best_monthly_price', fs.min_price,
            'power_hp', fs.v_power,
            'similarity_score_pct', ROUND(GREATEST(LEAST(75 + fs.category_score, 100), 50), 1),
            'similarity_reasons', jsonb_build_object(
                'base_price', fs.v_price_gross,
                'paid_options', (fs.synthesis_data->'card_summary'->'paid_options')
            )
        )
    FROM filtered_and_scored fs
    ORDER BY 
        CASE WHEN p_category = 'cheaper' THEN fs.v_price_gross END ASC,
        CASE WHEN p_category = 'stronger' THEN fs.v_power END DESC,
        CASE WHEN p_category = 'greener' THEN fs.v_eco_metric END ASC
    LIMIT p_limit;
END;
$function$;

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_alternatives_semantic(
    p_vehicle_id uuid,
    p_synthetic_vector vector(768),
    p_limit integer DEFAULT 5,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer
)
 RETURNS TABLE(similarity_json jsonb)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
DECLARE
    v_ref record;
BEGIN
    -- Base vehicle data
    SELECT
        (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS samar_category
    INTO v_ref
    FROM public.vehicle_synthesis vs
    WHERE vs.id = p_vehicle_id;

    IF v_ref.samar_category IS NULL THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT 
        jsonb_build_object(
            'vehicle_id', v.id,
            'brand', v.brand,
            'model', v.model,
            'version', COALESCE(v.synthesis_data->'card_summary'->>'trim_level', ''),
            'samar_category', COALESCE(v.synthesis_data->'mapped_ai_data'->>'samar_category', 'N/A'),
            'fuel', COALESCE(v.synthesis_data->'mapped_ai_data'->>'fuel', 'N/A'),
            'transmission', COALESCE(v.synthesis_data->'mapped_ai_data'->>'transmission', 'N/A'),
            'image_url', COALESCE(v.synthesis_data->>'image_url', ''),
            'power_hp', COALESCE((v.synthesis_data->'card_summary'->>'power_hp')::integer, (v.synthesis_data->'universal_features'->>'Moc silnika (KM)')::integer, 0),
            'similarity_score_pct', ROUND(((1 - (v.semantic_embedding <=> p_synthetic_vector)) * 100)::numeric, 2),
            'best_monthly_price', (
                SELECT MIN(monthly_price_net)
                FROM public.vehicle_matrix_cache mc
                WHERE mc.vehicle_id = v.id
                AND (p_duration_months IS NULL OR mc.duration_months = p_duration_months)
                AND (p_annual_mileage IS NULL OR mc.annual_mileage = p_annual_mileage)
            ),
            'similarity_reasons', jsonb_build_object(
                 'base_price', COALESCE(
                                    NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                                    NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                                    NULLIF(REGEXP_REPLACE(REPLACE(v.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                                    0
                               ),
                 'paid_options', (v.synthesis_data->'card_summary'->'paid_options')
            )
        )
    FROM public.vehicle_synthesis v
    WHERE v.id != p_vehicle_id
      AND v.semantic_embedding IS NOT NULL
      AND (v.synthesis_data->'mapped_ai_data'->>'samar_category')::text = v_ref.samar_category
      AND v.verification_status = 'completed'
    ORDER BY v.semantic_embedding <=> p_synthetic_vector
    LIMIT p_limit;
END;
$function$;
