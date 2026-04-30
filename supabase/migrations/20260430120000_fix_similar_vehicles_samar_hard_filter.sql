-- Fix: add SAMAR category as a hard filter in similar vehicles lookup.
-- When the reference vehicle has a SAMAR category, candidates must share it.
-- This prevents commercial vans / cross-segment mismatches caused by
-- incorrect body_style values in AI-extracted synthesis data.
CREATE OR REPLACE FUNCTION reverse_search.rpc_get_similar_vehicles(p_vehicle_id uuid, p_limit integer DEFAULT 5, p_duration_months integer DEFAULT NULL::integer, p_annual_mileage integer DEFAULT NULL::integer)
 RETURNS TABLE(vehicle_id uuid, brand character varying, model character varying, version character varying, samar_category character varying, fuel character varying, transmission character varying, best_monthly_price numeric, image_url character varying, similarity_score_pct numeric, suggested_discount_pct numeric, power_hp integer, body_style character varying, drive_type character varying, vehicle_class character varying, similarity_reasons jsonb)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
AS $function$
DECLARE
    v_ref record;
BEGIN
    SELECT
        vs.id,
        vs.brand,
        (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text AS samar_category,
        (vs.synthesis_data->'mapped_ai_data'->>'engine_class')::text AS engine_class,
        (vs.synthesis_data->'mapped_ai_data'->>'fuel')::text AS fuel,
        (vs.synthesis_data->'mapped_ai_data'->>'transmission')::text AS transmission,
        (vs.synthesis_data->'mapped_ai_data'->>'drive_type')::text AS drive_type,
        COALESCE(
            (vs.synthesis_data->'mapped_ai_data'->>'body_style')::text,
            (vs.synthesis_data->'card_summary'->>'body_style')::text,
            (vs.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
        ) AS body_style,
        COALESCE(
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
            0
        ) AS base_price_gross
    INTO v_ref
    FROM public.vehicle_synthesis vs
    WHERE vs.id = p_vehicle_id;

    IF v_ref.id IS NULL OR v_ref.base_price_gross = 0 THEN
        RETURN;
    END IF;

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
            COALESCE(
                (vs.synthesis_data->'mapped_ai_data'->>'body_style')::text,
                (vs.synthesis_data->'card_summary'->>'body_style')::text,
                (vs.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
            ) AS v_body,
            (vs.synthesis_data->>'image_url')::text AS v_image,
            (vs.synthesis_data->'card_summary'->>'suggested_discount_pct')::numeric AS v_discount,
            COALESCE(
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                0
            ) AS v_price,
            (vs.synthesis_data->'card_summary'->'paid_options') AS v_paid_options,
            GREATEST(0, 30.0 - (ABS(
                COALESCE(
                    NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->>'base_price', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                    NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'card_summary'->'parsed_prices'->>'base', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                    NULLIF(REGEXP_REPLACE(REPLACE(vs.synthesis_data->'universal_features'->>'cena_pojazdu', ',', '.'), '[^0-9\.]', '', 'g'), '')::numeric,
                    0
                ) - v_ref.base_price_gross
            ) / v_ref.base_price_gross * 100.0) * (30.0 / 25.0)) AS score_price,
            CASE WHEN
                COALESCE(
                    (vs.synthesis_data->'mapped_ai_data'->>'body_style')::text,
                    (vs.synthesis_data->'card_summary'->>'body_style')::text,
                    (vs.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text
                ) = v_ref.body_style AND v_ref.body_style IS NOT NULL
            THEN 20 ELSE 0 END AS score_body,
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'fuel') = v_ref.fuel AND v_ref.fuel IS NOT NULL THEN 15 ELSE 0 END AS score_fuel,
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'transmission') = v_ref.transmission AND v_ref.transmission IS NOT NULL THEN 15 ELSE 0 END AS score_trans,
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'drive_type') = v_ref.drive_type AND v_ref.drive_type IS NOT NULL THEN 10 ELSE 0 END AS score_drive,
            CASE WHEN (vs.synthesis_data->'mapped_ai_data'->>'samar_category') = v_ref.samar_category AND v_ref.samar_category IS NOT NULL THEN 10 ELSE 0 END AS score_samar,
            COALESCE((vs.synthesis_data->'card_summary'->>'power_hp')::integer, (vs.synthesis_data->'universal_features'->>'Moc silnika (KM)')::integer, 0) as v_power,
            COALESCE((vs.synthesis_data->'card_summary'->>'body_style')::text, (vs.synthesis_data->'universal_features'->>'Rodzaj nadwozia')::text, 'N/A') as v_body_style,
            COALESCE((vs.synthesis_data->'card_summary'->>'drivetrain')::text, (vs.synthesis_data->'universal_features'->>'Typ napędu')::text, 'N/A') as v_drive_type,
            COALESCE((vs.synthesis_data->'card_summary'->>'samar_category')::text, (vs.synthesis_data->'mapped_ai_data'->>'samar_category')::text, 'N/A') as v_class_name
        FROM public.vehicle_synthesis vs
        WHERE vs.id != p_vehicle_id
          AND vs.verification_status = 'completed'
    ),
    filtered_candidates AS (
        SELECT *,
               (score_price + score_body + score_fuel + score_trans + score_drive + score_samar) AS base_relevance
        FROM candidates
        WHERE v_price BETWEEN v_ref.base_price_gross * 0.75 AND v_ref.base_price_gross * 1.25
          AND score_body = 20
          AND (v_ref.samar_category IS NULL OR score_samar = 10)  -- hard filter: same segment when known
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
    ),
    final_output AS (
        SELECT
            c.v_id::uuid,
            c.brand::varchar,
            c.model::varchar,
            c.version::varchar,
            COALESCE(c.v_samar, 'N/A')::varchar as samar_cat,
            COALESCE(c.v_fuel, 'N/A')::varchar as fuel_str,
            COALESCE(c.v_transmission, 'N/A')::varchar as trans,
            bp.min_price::numeric,
            c.v_image::varchar,
            LEAST(100.0, ROUND(
                (c.base_relevance * 0.8) +
                ((COALESCE(sf.shared, 0)::numeric / (SELECT total FROM ref_count)) * 100 * 0.2),
                1
            ))::numeric AS similarity_score_pct,
            c.v_discount::numeric,
            c.v_power::integer,
            c.v_body_style::varchar,
            c.v_drive_type::varchar,
            c.v_class_name::varchar,
            ROUND((COALESCE(sf.shared, 0)::numeric / (SELECT total FROM ref_count)) * 100, 1) as shared_equip_pct,
            c.score_samar,
            c.score_body,
            c.score_fuel,
            c.score_drive,
            c.v_price,
            c.v_paid_options,
            c.base_relevance
        FROM filtered_candidates c
        JOIN best_prices bp ON bp.v_id = c.v_id
        LEFT JOIN shared_features sf ON sf.v_id = c.v_id
        WHERE c.base_relevance >= 30
    )
    SELECT
        f.v_id,
        f.brand,
        f.model,
        f.version,
        f.samar_cat as samar_category,
        f.fuel_str as fuel,
        f.trans as transmission,
        f.min_price as best_monthly_price,
        f.v_image as image_url,
        f.similarity_score_pct,
        f.v_discount as suggested_discount_pct,
        f.v_power as power_hp,
        f.v_body_style as body_style,
        f.v_drive_type as drive_type,
        f.v_class_name as vehicle_class,
        jsonb_build_object(
            'samar_match',     (f.score_samar > 0),
            'body_match',      (f.score_body > 0),
            'fuel_match',      (f.score_fuel > 0),
            'drive_match',     (f.score_drive > 0),
            'equipment_match', (f.shared_equip_pct > 60),
            'equipment_similarity_pct', f.shared_equip_pct,
            'is_same_brand',   (f.brand = v_ref.brand AND v_ref.brand IS NOT NULL),
            'price_pct_diff',  ROUND(ABS(f.v_price - v_ref.base_price_gross) / GREATEST(v_ref.base_price_gross, 1) * 100, 1),
            'samar_category',  f.samar_cat,
            'body_style',      COALESCE(f.v_body_style, 'N/A'),
            'base_price',      f.v_price,
            'paid_options',    f.v_paid_options
        )::jsonb AS similarity_reasons
    FROM final_output f
    ORDER BY
        f.similarity_score_pct DESC,
        CASE WHEN f.min_price IS NULL THEN 1 ELSE 0 END ASC,
        f.min_price ASC NULLS LAST
    LIMIT p_limit;
END;
$function$;
