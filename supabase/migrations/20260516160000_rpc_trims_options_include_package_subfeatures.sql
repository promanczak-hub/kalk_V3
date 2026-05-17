-- Extend rpc_get_trims_and_options so the "Cechy dedykowane" picker also surfaces
-- sub-features that exist only as decomposed package components (e.g. "system 360"
-- nested inside "Pakiet Technology Premium").
--
-- Data path:
--   public.vehicle_synthesis.synthesis_data->card_summary->paid_options[]      (top-level)
--   reverse_search.vehicle_feature_evidence WHERE source_type='package_decomposition'
--     joined with reverse_search.universal_features for canonical display_name,
--     parent package extracted from value_text "<name> (z: <package>)".
--
-- Response shape adds two optional fields per option item:
--   is_sub_feature  : true when this name is ONLY reachable via package decomposition
--                     (no vehicle has it as a standalone paid_options[].name)
--   parent_packages : list of distinct package names the sub-feature belongs to
--                     (empty when is_sub_feature=false)

DROP FUNCTION IF EXISTS public.rpc_get_trims_and_options(text[], text[], text[], text[], text[], text[], text[]);
DROP FUNCTION IF EXISTS reverse_search.rpc_get_trims_and_options(text[], text[], text[], text[], text[], text[], text[]);

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

    -- ── paid_options: top-level packages UNIONed with decomposed sub-features ──
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
    ),
    paid_rows AS (
        -- Top-level paid options: package/standalone option names from card_summary.
        SELECT c.id AS vid,
               jsonb_array_elements(COALESCE(c.synthesis_data->'card_summary'->'paid_options', '[]'::jsonb))->>'name' AS opt_name,
               false AS is_sub,
               NULL::text AS parent_pkg
        FROM candidates c
        UNION ALL
        -- Decomposed sub-features: canonical display_name from universal_features,
        -- parent package extracted from value_text via "(z: <package>)" suffix.
        SELECT vfe.source_vehicle_id AS vid,
               uf.display_name AS opt_name,
               true AS is_sub,
               NULLIF(TRIM(BOTH FROM (regexp_match(vfe.value_text, '\(z:\s*(.+?)\)\s*$'))[1]), '') AS parent_pkg
        FROM reverse_search.vehicle_feature_evidence vfe
        JOIN reverse_search.universal_features uf ON uf.id = vfe.feature_id
        JOIN candidates c ON c.id = vfe.source_vehicle_id
        WHERE vfe.source_type = 'package_decomposition'
          AND uf.display_name IS NOT NULL
          AND TRIM(uf.display_name) <> ''
    )
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'name', opt_name,
                'count', cnt,
                'is_sub_feature', is_sub_only,
                'parent_packages', COALESCE(parent_pkgs, '[]'::jsonb)
            )
            ORDER BY cnt DESC
        ),
        '[]'::jsonb
    )
    INTO v_paid
    FROM (
        SELECT opt_name,
               COUNT(DISTINCT vid) AS cnt,
               -- "Sub-feature only" iff EVERY occurrence is via package decomposition.
               -- If any vehicle has it directly as paid_options[].name, treat as
               -- regular top-level so the picker doesn't mislead.
               BOOL_AND(is_sub) AS is_sub_only,
               CASE
                   WHEN BOOL_AND(is_sub) THEN
                       (SELECT COALESCE(jsonb_agg(DISTINCT pkg), '[]'::jsonb)
                        FROM unnest(ARRAY_AGG(parent_pkg) FILTER (WHERE parent_pkg IS NOT NULL)) AS pkg)
                   ELSE '[]'::jsonb
               END AS parent_pkgs
        FROM paid_rows
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
