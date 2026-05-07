-- Extend rpc_get_trims_and_options to accept narrowing filters beyond brand/model.
-- Adds 5 new parameters (body types, samar class names, transmissions, drive types, fuel
-- types) so the "Cechy dedykowane" tab can aggregate options whenever any filter is
-- active, not only when the user picks a brand or model.
--
-- Drops the old 2-arg overloads first to avoid PostgREST ambiguity when calling with
-- named parameters (CREATE OR REPLACE only matches the same signature, so adding
-- DEFAULTs to a wider signature would create a parallel overload, not replace).

DROP FUNCTION IF EXISTS public.rpc_get_trims_and_options(text[], text[]);
DROP FUNCTION IF EXISTS reverse_search.rpc_get_trims_and_options(text[], text[]);

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_trims_and_options(
    p_brands              text[] DEFAULT NULL,
    p_models              text[] DEFAULT NULL,
    p_body_types          text[] DEFAULT NULL,
    p_samar_class_names   text[] DEFAULT NULL,
    p_transmissions       text[] DEFAULT NULL,
    p_drive_types         text[] DEFAULT NULL,
    p_fuel_types          text[] DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql
STABLE
AS $function$
DECLARE
    v_trims jsonb;
    v_std jsonb;
    v_paid jsonb;
BEGIN
    WITH candidates AS (
        SELECT vs.id, vs.synthesis_data
        FROM public.vehicle_synthesis vs
        WHERE vs.verification_status = 'completed'
          AND (p_brands IS NULL OR array_length(p_brands, 1) IS NULL
               OR LOWER(vs.brand) = ANY(SELECT LOWER(unnest) FROM unnest(p_brands)))
          AND (p_models IS NULL OR array_length(p_models, 1) IS NULL
               OR LOWER(vs.model) = ANY(SELECT LOWER(unnest) FROM unnest(p_models)))
          AND (p_body_types IS NULL OR array_length(p_body_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'body_style',
                    vs.synthesis_data->'card_summary'->>'body_style'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_body_types)))
          AND (p_samar_class_names IS NULL OR array_length(p_samar_class_names, 1) IS NULL
               OR LOWER(vs.synthesis_data->'mapped_ai_data'->>'samar_category')
                  = ANY(SELECT LOWER(unnest) FROM unnest(p_samar_class_names)))
          AND (p_transmissions IS NULL OR array_length(p_transmissions, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'gearbox',
                    vs.synthesis_data->'card_summary'->>'transmission'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_transmissions)))
          AND (p_drive_types IS NULL OR array_length(p_drive_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'drive_type',
                    vs.synthesis_data->'card_summary'->>'drive_type',
                    vs.synthesis_data->'card_summary'->>'drivetrain'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_drive_types)))
          AND (p_fuel_types IS NULL OR array_length(p_fuel_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'fuel',
                    vs.synthesis_data->'card_summary'->>'fuel'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_fuel_types)))
    )
    SELECT COALESCE(jsonb_agg(jsonb_build_object('name', trim_level, 'count', cnt) ORDER BY cnt DESC), '[]'::jsonb)
    INTO v_trims
    FROM (
        SELECT c.synthesis_data->'card_summary'->>'trim_level' AS trim_level, COUNT(*) AS cnt
        FROM candidates c
        WHERE c.synthesis_data->'card_summary'->>'trim_level' IS NOT NULL
        GROUP BY trim_level
    ) t;

    WITH candidates AS (
        SELECT vs.id, vs.synthesis_data
        FROM public.vehicle_synthesis vs
        WHERE vs.verification_status = 'completed'
          AND (p_brands IS NULL OR array_length(p_brands, 1) IS NULL
               OR LOWER(vs.brand) = ANY(SELECT LOWER(unnest) FROM unnest(p_brands)))
          AND (p_models IS NULL OR array_length(p_models, 1) IS NULL
               OR LOWER(vs.model) = ANY(SELECT LOWER(unnest) FROM unnest(p_models)))
          AND (p_body_types IS NULL OR array_length(p_body_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'body_style',
                    vs.synthesis_data->'card_summary'->>'body_style'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_body_types)))
          AND (p_samar_class_names IS NULL OR array_length(p_samar_class_names, 1) IS NULL
               OR LOWER(vs.synthesis_data->'mapped_ai_data'->>'samar_category')
                  = ANY(SELECT LOWER(unnest) FROM unnest(p_samar_class_names)))
          AND (p_transmissions IS NULL OR array_length(p_transmissions, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'gearbox',
                    vs.synthesis_data->'card_summary'->>'transmission'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_transmissions)))
          AND (p_drive_types IS NULL OR array_length(p_drive_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'drive_type',
                    vs.synthesis_data->'card_summary'->>'drive_type',
                    vs.synthesis_data->'card_summary'->>'drivetrain'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_drive_types)))
          AND (p_fuel_types IS NULL OR array_length(p_fuel_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'fuel',
                    vs.synthesis_data->'card_summary'->>'fuel'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_fuel_types)))
    )
    SELECT COALESCE(jsonb_agg(jsonb_build_object('name', opt_name, 'count', cnt) ORDER BY cnt DESC), '[]'::jsonb)
    INTO v_std
    FROM (
        SELECT opt_name, COUNT(DISTINCT vid) AS cnt
        FROM (
            SELECT c.id AS vid,
                   jsonb_array_elements_text(COALESCE(c.synthesis_data->'card_summary'->'standard_equipment', '[]'::jsonb)) AS opt_name
            FROM candidates c
        ) opts
        WHERE opt_name IS NOT NULL AND TRIM(opt_name) <> ''
        GROUP BY opt_name
    ) std;

    WITH candidates AS (
        SELECT vs.id, vs.synthesis_data
        FROM public.vehicle_synthesis vs
        WHERE vs.verification_status = 'completed'
          AND (p_brands IS NULL OR array_length(p_brands, 1) IS NULL
               OR LOWER(vs.brand) = ANY(SELECT LOWER(unnest) FROM unnest(p_brands)))
          AND (p_models IS NULL OR array_length(p_models, 1) IS NULL
               OR LOWER(vs.model) = ANY(SELECT LOWER(unnest) FROM unnest(p_models)))
          AND (p_body_types IS NULL OR array_length(p_body_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'body_style',
                    vs.synthesis_data->'card_summary'->>'body_style'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_body_types)))
          AND (p_samar_class_names IS NULL OR array_length(p_samar_class_names, 1) IS NULL
               OR LOWER(vs.synthesis_data->'mapped_ai_data'->>'samar_category')
                  = ANY(SELECT LOWER(unnest) FROM unnest(p_samar_class_names)))
          AND (p_transmissions IS NULL OR array_length(p_transmissions, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'gearbox',
                    vs.synthesis_data->'card_summary'->>'transmission'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_transmissions)))
          AND (p_drive_types IS NULL OR array_length(p_drive_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'drive_type',
                    vs.synthesis_data->'card_summary'->>'drive_type',
                    vs.synthesis_data->'card_summary'->>'drivetrain'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_drive_types)))
          AND (p_fuel_types IS NULL OR array_length(p_fuel_types, 1) IS NULL
               OR LOWER(COALESCE(
                    vs.synthesis_data->'mapped_ai_data'->>'fuel',
                    vs.synthesis_data->'card_summary'->>'fuel'
                  )) = ANY(SELECT LOWER(unnest) FROM unnest(p_fuel_types)))
    )
    SELECT COALESCE(jsonb_agg(jsonb_build_object('name', opt_name, 'count', cnt) ORDER BY cnt DESC), '[]'::jsonb)
    INTO v_paid
    FROM (
        SELECT opt_name, COUNT(DISTINCT vid) AS cnt
        FROM (
            SELECT c.id AS vid,
                   jsonb_array_elements(COALESCE(c.synthesis_data->'card_summary'->'paid_options', '[]'::jsonb))->>'name' AS opt_name
            FROM candidates c
        ) opts
        WHERE opt_name IS NOT NULL AND TRIM(opt_name) <> ''
        GROUP BY opt_name
    ) pd;

    RETURN jsonb_build_object(
        'trim_levels', COALESCE(v_trims, '[]'::jsonb),
        'standard_options', COALESCE(v_std, '[]'::jsonb),
        'paid_options', COALESCE(v_paid, '[]'::jsonb)
    );
END;
$function$;

CREATE OR REPLACE FUNCTION public.rpc_get_trims_and_options(
    p_brands              text[] DEFAULT NULL,
    p_models              text[] DEFAULT NULL,
    p_body_types          text[] DEFAULT NULL,
    p_samar_class_names   text[] DEFAULT NULL,
    p_transmissions       text[] DEFAULT NULL,
    p_drive_types         text[] DEFAULT NULL,
    p_fuel_types          text[] DEFAULT NULL
) RETURNS jsonb
LANGUAGE sql
SET search_path TO ''
AS $function$
    SELECT reverse_search.rpc_get_trims_and_options(
        p_brands, p_models, p_body_types, p_samar_class_names,
        p_transmissions, p_drive_types, p_fuel_types
    );
$function$;
