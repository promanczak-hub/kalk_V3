-- Expose the two scoring components from public.rpc_reverse_search.
--
-- Total match_score_pct = LEAST(100, features_pct + semantic_points).
-- Until now only the blended total reached the API. Without the breakdown the
-- UI cannot tell users *why* a vehicle ranked where it did. This migration
-- adds two extra return columns:
--   * score_features_pct — (matched_weight / total_weight) * 100, capped at 100
--   * score_semantic     — (1 - cosine_distance) * 30 when a semantic query
--                          vector is provided, else 0
--
-- Body of the function is unchanged otherwise — only the RETURNS TABLE shape
-- and the final SELECT add two more columns.

DROP FUNCTION IF EXISTS public.rpc_reverse_search(jsonb, text[], text[], integer[], text[], uuid[], text, vector);

CREATE OR REPLACE FUNCTION public.rpc_reverse_search(
    p_requirements jsonb DEFAULT '[]'::jsonb,
    p_brands text[] DEFAULT NULL::text[],
    p_models text[] DEFAULT NULL::text[],
    p_samar_class_ids integer[] DEFAULT NULL::integer[],
    p_trims text[] DEFAULT NULL::text[],
    p_vehicle_ids uuid[] DEFAULT NULL::uuid[],
    p_search_query text DEFAULT NULL::text,
    p_semantic_query_vector vector DEFAULT NULL::vector
)
RETURNS TABLE(
    vehicle_id uuid,
    brand text,
    model text,
    version text,
    match_score_pct numeric,
    score_features_pct numeric,
    score_semantic numeric,
    matched_features jsonb,
    missing_features jsonb,
    best_monthly_price numeric,
    applied_margin_pct numeric,
    fuel_type text,
    power_hp integer,
    transmission text,
    body_style text,
    drive_type text,
    base_price_raw text,
    options_price_raw text,
    total_price_raw text,
    price_domain text,
    suggested_discount_pct numeric,
    trim_level text,
    vehicle_class text,
    has_ltr_cache boolean,
    service_cost_type text,
    tire_class text,
    offer_number text,
    configuration_code text
)
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_total_weight numeric := 0;
BEGIN
    SELECT COALESCE(SUM((r->>'weight')::numeric), 0) INTO v_total_weight
    FROM jsonb_array_elements(COALESCE(p_requirements, '[]'::jsonb)) r
    WHERE r->>'feature_key' NOT IN
        ('duration_months','annual_mileage','margin_pct','monthly_price_net');
    IF v_total_weight = 0 THEN
        v_total_weight := 1;
    END IF;

    RETURN QUERY
    WITH target AS (
        SELECT
            vs.id                                                  AS v_id,
            vs.brand                                               AS brand,
            vs.model                                               AS model,
            vs.synthesis_data -> 'card_summary'                    AS cs,
            vs.synthesis_data -> 'mapped_ai_data'                  AS mad,
            vs.synthesis_data -> 'calculator_setup'                AS setup,
            vs.synthesis_data ->> 'configuration_code'             AS config_code,
            vs.offer_number                                        AS offer_number,
            vs.semantic_embedding                                  AS semantic_embedding,
            vs.feature_keys_present                                AS feature_keys
        FROM public.vehicle_synthesis vs
        WHERE
            (p_brands IS NULL OR array_length(p_brands,1) IS NULL
              OR LOWER(vs.brand) = ANY(SELECT LOWER(unnest) FROM unnest(p_brands)))
          AND (p_models IS NULL OR array_length(p_models,1) IS NULL
              OR LOWER(vs.model) = ANY(SELECT LOWER(unnest) FROM unnest(p_models)))
          AND (p_samar_class_ids IS NULL OR array_length(p_samar_class_ids,1) IS NULL
              OR (vs.synthesis_data->>'samar_class_id')::int = ANY(p_samar_class_ids))
          AND (p_trims IS NULL OR array_length(p_trims,1) IS NULL
              OR LOWER(vs.synthesis_data->'card_summary'->>'trim_level')
                 = ANY(SELECT LOWER(unnest) FROM unnest(p_trims)))
          AND (p_vehicle_ids IS NULL OR array_length(p_vehicle_ids,1) IS NULL
              OR vs.id = ANY(p_vehicle_ids))
    ),
    matrix_ctx AS (
        SELECT
            MAX(CASE WHEN r->>'feature_key'='duration_months' AND r->>'operator'='gte' THEN (r->>'value')::numeric END) AS dur_min,
            MAX(CASE WHEN r->>'feature_key'='duration_months' AND r->>'operator'='lte' THEN (r->>'value')::numeric END) AS dur_max,
            MAX(CASE WHEN r->>'feature_key'='duration_months' AND r->>'operator'='eq'  THEN (r->>'value')::numeric END) AS dur_eq,
            MAX(CASE WHEN r->>'feature_key'='annual_mileage'  AND r->>'operator'='gte' THEN (r->>'value')::numeric END) AS mil_min,
            MAX(CASE WHEN r->>'feature_key'='annual_mileage'  AND r->>'operator'='lte' THEN (r->>'value')::numeric END) AS mil_max,
            MAX(CASE WHEN r->>'feature_key'='annual_mileage'  AND r->>'operator'='eq'  THEN (r->>'value')::numeric END) AS mil_eq,
            MAX(CASE WHEN r->>'feature_key'='margin_pct'      AND r->>'operator'='gte' THEN (r->>'value')::numeric END) AS margin_min,
            MAX(CASE WHEN r->>'feature_key'='monthly_price_net' AND r->>'operator'='lte' THEN (r->>'value')::numeric END) AS budget_max
        FROM jsonb_array_elements(COALESCE(p_requirements, '[]'::jsonb)) r
    ),
    matrix_base AS (
        SELECT
            vmc.vehicle_id AS v_id,
            MIN(vmc.monthly_price_net) AS base_price
        FROM public.vehicle_matrix_cache vmc
        CROSS JOIN matrix_ctx ctx
        WHERE vmc.margin_pct = 0
          AND (ctx.dur_min IS NULL OR vmc.duration_months >= ctx.dur_min)
          AND (ctx.dur_max IS NULL OR vmc.duration_months <= ctx.dur_max)
          AND (ctx.dur_eq  IS NULL OR vmc.duration_months  = ctx.dur_eq)
          AND (ctx.mil_min IS NULL OR vmc.annual_mileage   >= ctx.mil_min)
          AND (ctx.mil_max IS NULL OR vmc.annual_mileage   <= ctx.mil_max)
          AND (ctx.mil_eq  IS NULL OR vmc.annual_mileage    = ctx.mil_eq)
        GROUP BY vmc.vehicle_id
    ),
    matrix_best AS (
        SELECT
            mb.v_id,
            mb.base_price,
            m.effective_margin,
            ROUND(mb.base_price / NULLIF(1.0 - m.effective_margin / 100.0, 0), 0) AS price,
            TRUE AS has_cache
        FROM matrix_base mb
        CROSS JOIN matrix_ctx ctx
        CROSS JOIN LATERAL (
            SELECT CASE
                WHEN ctx.budget_max IS NULL THEN COALESCE(ctx.margin_min, 0)
                WHEN mb.base_price IS NULL OR mb.base_price <= 0 THEN COALESCE(ctx.margin_min, 0)
                ELSE GREATEST(
                    COALESCE(ctx.margin_min, 0),
                    LEAST(35, FLOOR((1.0 - mb.base_price / ctx.budget_max) * 100))
                )
            END AS effective_margin
        ) m
    ),
    evals AS (
        SELECT
            t.v_id, t.brand, t.model, t.cs, t.mad, t.setup, t.config_code,
            t.offer_number, t.semantic_embedding,
            r->>'feature_key' AS feature_key,
            r->>'requirement' AS requirement,
            COALESCE((r->>'weight')::numeric, 1) AS weight,
            mb.price AS best_price,
            mb.effective_margin AS effective_margin,
            COALESCE(mb.has_cache, FALSE) AS has_cache,
            COALESCE(
              CASE
                WHEN r->>'feature_key' IN ('duration_months','annual_mileage','margin_pct') THEN TRUE
                WHEN r->>'feature_key' = '__none' THEN TRUE
                WHEN r->>'feature_key' = 'monthly_price_net' THEN
                    CASE
                        WHEN r->>'operator'='lte' AND mb.price <= (r->>'value')::numeric * 1.05 THEN TRUE
                        WHEN r->>'operator'='gte' AND mb.price >= (r->>'value')::numeric * 0.95 THEN TRUE
                        ELSE FALSE
                    END
                WHEN r->>'feature_key' LIKE 'opt_std:%' THEN
                    COALESCE(t.cs->'standard_equipment', '[]'::jsonb)
                        @> jsonb_build_array(SUBSTRING(r->>'feature_key' FROM 9))
                WHEN r->>'feature_key' LIKE 'opt_paid:%' THEN
                    EXISTS (
                        SELECT 1 FROM jsonb_array_elements(COALESCE(t.cs->'paid_options','[]'::jsonb)) po
                        WHERE po->>'name' = SUBSTRING(r->>'feature_key' FROM 10)
                    )
                WHEN r->>'operator' = 'in' THEN
                    COALESCE(r->'value', '[]'::jsonb) @> to_jsonb(
                        CASE r->>'feature_key'
                            WHEN 'body_style'    THEN t.cs->>'body_style'
                            WHEN 'drive_type'    THEN COALESCE(t.mad->>'drive_type',    t.cs->>'drive_type')
                            WHEN 'transmission'  THEN COALESCE(t.mad->>'gearbox',       t.cs->>'transmission')
                            WHEN 'gearbox'       THEN COALESCE(t.mad->>'gearbox',       t.cs->>'transmission')
                            WHEN 'fuel'          THEN COALESCE(t.mad->>'fuel',          t.cs->>'fuel')
                            WHEN 'vehicle_class' THEN COALESCE(t.mad->>'vehicle_type',  t.cs->>'vehicle_class')
                            WHEN 'trim_level'    THEN t.cs->>'trim_level'
                            ELSE NULL
                        END
                    )
                WHEN r->>'operator' = 'eq' AND r->>'value' IN ('true','false') THEN
                    CASE WHEN r->>'value' = 'true'
                         THEN (r->>'feature_key') = ANY(COALESCE(t.feature_keys, ARRAY[]::text[]))
                         ELSE NOT ((r->>'feature_key') = ANY(COALESCE(t.feature_keys, ARRAY[]::text[])))
                    END
                WHEN r->>'operator' = 'eq' THEN
                    CASE r->>'feature_key'
                        WHEN 'body_style'    THEN LOWER(t.cs->>'body_style')                                         = LOWER(r->>'value')
                        WHEN 'drive_type'    THEN LOWER(COALESCE(t.mad->>'drive_type',    t.cs->>'drive_type'))      = LOWER(r->>'value')
                        WHEN 'transmission'  THEN LOWER(COALESCE(t.mad->>'gearbox',       t.cs->>'transmission'))    = LOWER(r->>'value')
                        WHEN 'gearbox'       THEN LOWER(COALESCE(t.mad->>'gearbox',       t.cs->>'transmission'))    = LOWER(r->>'value')
                        WHEN 'fuel'          THEN LOWER(COALESCE(t.mad->>'fuel',          t.cs->>'fuel'))            = LOWER(r->>'value')
                        WHEN 'vehicle_class' THEN LOWER(COALESCE(t.mad->>'vehicle_type',  t.cs->>'vehicle_class'))   = LOWER(r->>'value')
                        WHEN 'trim_level'    THEN LOWER(t.cs->>'trim_level')                                         = LOWER(r->>'value')
                        ELSE (r->>'feature_key') = ANY(COALESCE(t.feature_keys, ARRAY[]::text[]))
                    END
                WHEN r->>'operator' = 'gte' THEN
                    CASE r->>'feature_key'
                        WHEN 'power_hp' THEN NULLIF(t.cs->>'power_hp','')::numeric >= (r->>'value')::numeric
                        ELSE FALSE
                    END
                WHEN r->>'operator' = 'lte' THEN
                    CASE r->>'feature_key'
                        WHEN 'power_hp' THEN NULLIF(t.cs->>'power_hp','')::numeric <= (r->>'value')::numeric
                        ELSE FALSE
                    END
                ELSE FALSE
              END,
              FALSE
            ) AS is_match
        FROM target t
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE WHEN jsonb_array_length(COALESCE(p_requirements, '[]'::jsonb)) > 0
                 THEN p_requirements
                 ELSE '[{"feature_key":"__none","requirement":"NICE_TO_HAVE","weight":0,"operator":"eq","value":""}]'::jsonb
            END
        ) AS r
        LEFT JOIN matrix_best mb ON mb.v_id = t.v_id
    ),
    failed_must_haves AS (
        SELECT DISTINCT v_id FROM evals
        WHERE requirement = 'MUST_HAVE' AND is_match = FALSE
    ),
    survivors AS (
        SELECT
            e.v_id, e.brand, e.model, e.cs, e.mad, e.setup, e.config_code,
            e.offer_number, e.semantic_embedding,
            MIN(e.best_price)            AS price,
            MIN(e.effective_margin)      AS effective_margin,
            BOOL_OR(e.has_cache)         AS has_cache,
            SUM(CASE WHEN e.is_match
                       AND e.feature_key NOT IN ('duration_months','annual_mileage','margin_pct','monthly_price_net','__none')
                     THEN e.weight ELSE 0 END) AS score,
            JSONB_AGG(e.feature_key) FILTER (
                WHERE e.is_match
                  AND e.feature_key NOT IN ('duration_months','annual_mileage','margin_pct','monthly_price_net','__none')
            ) AS matched,
            JSONB_AGG(e.feature_key) FILTER (
                WHERE NOT e.is_match
                  AND e.feature_key NOT IN ('duration_months','annual_mileage','margin_pct','monthly_price_net','__none')
            ) AS missing
        FROM evals e
        WHERE e.v_id NOT IN (SELECT v_id FROM failed_must_haves)
        GROUP BY e.v_id, e.brand, e.model, e.cs, e.mad, e.setup, e.config_code, e.offer_number, e.semantic_embedding
    ),
    components AS (
        SELECT
            s.*,
            ROUND(LEAST(100.0, (s.score / v_total_weight) * 100)::numeric, 2) AS c_features_pct,
            ROUND(
                CASE
                    WHEN p_semantic_query_vector IS NOT NULL AND s.semantic_embedding IS NOT NULL
                    THEN GREATEST(0, (1 - (s.semantic_embedding <=> p_semantic_query_vector))) * 30.0
                    ELSE 0
                END::numeric,
                2
            ) AS c_semantic
        FROM survivors s
    )
    SELECT
        c.v_id                                                 AS vehicle_id,
        c.brand                                                AS brand,
        c.model                                                AS model,
        c.cs->>'powertrain'                                    AS version,
        ROUND(LEAST(100.0, (c.c_features_pct + c.c_semantic))::numeric, 2) AS match_score_pct,
        c.c_features_pct                                       AS score_features_pct,
        c.c_semantic                                           AS score_semantic,
        COALESCE(c.matched, '[]'::jsonb)                       AS matched_features,
        COALESCE(c.missing, '[]'::jsonb)                       AS missing_features,
        c.price                                                AS best_monthly_price,
        c.effective_margin                                     AS applied_margin_pct,
        COALESCE(c.mad->>'fuel',          c.cs->>'fuel')         AS fuel_type,
        NULLIF(c.cs->>'power_hp','')::int                        AS power_hp,
        COALESCE(c.mad->>'gearbox',       c.cs->>'transmission') AS transmission,
        c.cs->>'body_style'                                      AS body_style,
        COALESCE(c.mad->>'drive_type',    c.cs->>'drive_type')   AS drive_type,
        c.cs->>'base_price'                                      AS base_price_raw,
        c.cs->>'options_price'                                   AS options_price_raw,
        c.cs->>'total_price'                                     AS total_price_raw,
        COALESCE(c.cs->>'price_domain', c.cs->>'_price_domain', 'brutto') AS price_domain,
        NULLIF(c.cs->>'suggested_discount_pct','')::numeric      AS suggested_discount_pct,
        c.cs->>'trim_level'                                      AS trim_level,
        COALESCE(c.mad->>'vehicle_type',  c.cs->>'vehicle_class') AS vehicle_class,
        c.has_cache                                              AS has_ltr_cache,
        c.setup->>'service_cost_type'                            AS service_cost_type,
        c.setup->'tire_params'->>'tire_class'                    AS tire_class,
        c.offer_number                                           AS offer_number,
        c.config_code                                            AS configuration_code
    FROM components c
    ORDER BY match_score_pct DESC, c.brand, c.model
    LIMIT 200;
END;
$function$;
