-- =============================================================
-- Migration: Update RPCs for Multi-Filter (Brands, Models, Classes)
-- ISOLATION: public / reverse_search schema
-- =============================================================

-- Drop old functions with old signatures
DROP FUNCTION IF EXISTS public.rpc_reverse_search(text, jsonb);
DROP FUNCTION IF EXISTS reverse_search.rpc_reverse_search(text, jsonb);
DROP FUNCTION IF EXISTS public.rpc_reverse_search(jsonb, text[], text[], integer[]);
DROP FUNCTION IF EXISTS reverse_search.rpc_reverse_search(jsonb, text[], text[], integer[]);
DROP FUNCTION IF EXISTS public.rpc_get_available_filters(text, jsonb);
DROP FUNCTION IF EXISTS reverse_search.rpc_get_available_filters(text, jsonb);


-- ==========================================
-- 1. rpc_reverse_search
-- ==========================================
CREATE OR REPLACE FUNCTION reverse_search.rpc_reverse_search(
    p_requirements jsonb,
    p_brands text[] DEFAULT NULL,
    p_models text[] DEFAULT NULL,
    p_samar_class_ids int[] DEFAULT NULL
)
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, match_score_pct numeric, matched_features jsonb, missing_features jsonb, best_monthly_price numeric)
 LANGUAGE plpgsql
AS $function$
declare
    v_total_possible_score numeric := 0;
begin
    select coalesce(sum((r->>'weight')::numeric), 0) into v_total_possible_score
    from jsonb_array_elements(p_requirements) as r
    where r->>'feature_key' not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net');

    if v_total_possible_score = 0 then
        v_total_possible_score := 1;
    end if;

    return query
    with target_vehicles as (
        select vs.id as v_id,
               vs.brand,
               vs.model,
               vs.synthesis_data->>'version' as version
        from public.vehicle_synthesis vs
        left join public.samar_classes sc on sc.id = (vs.synthesis_data->>'samar_class_id')::int
        where 
            (p_brands is null or array_length(p_brands, 1) is null or lower(vs.synthesis_data->>'brand') = any(select lower(unnest) from unnest(p_brands)))
            and (p_models is null or array_length(p_models, 1) is null or lower(vs.synthesis_data->>'model') = any(select lower(unnest) from unnest(p_models)))
            and (p_samar_class_ids is null or array_length(p_samar_class_ids, 1) is null or sc.id = any(p_samar_class_ids))
    ),
    matrix_context as (
        select 
            max(case when req->>'feature_key' = 'duration_months' then (req->>'value')::numeric else null end) as req_duration,
            max(case when req->>'feature_key' = 'annual_mileage' then (req->>'value')::numeric else null end) as req_mileage,
            max(case when req->>'feature_key' = 'margin_pct' then (req->>'value')::numeric else null end) as req_margin
        from jsonb_array_elements(p_requirements) as req
    ),
    vehicle_matrix_best as (
        select vmc.vehicle_id as v_id, 
               min(vmc.monthly_price_net) as best_monthly_price
        from public.vehicle_matrix_cache vmc
        cross join matrix_context ctx
        where (ctx.req_duration is null or vmc.duration_months = ctx.req_duration)
          and (ctx.req_mileage is null or vmc.annual_mileage = ctx.req_mileage)
          and (ctx.req_margin is null or vmc.margin_pct >= ctx.req_margin)
        group by vmc.vehicle_id
    ),
    vehicle_evals as (
        select tv.v_id, tv.brand, tv.model, tv.version,
               req->>'feature_key' as feature_key,
               req->>'requirement' as requirement,
               (req->>'weight')::numeric as weight,
               vfs.resolved_value_bool,
               vfs.resolved_value_num,
               vfs.resolved_value_text,
               vmb.best_monthly_price,
               case 
                   when req->>'feature_key' = 'monthly_price_net' then
                       case 
                           when req->>'operator' = 'lte' and vmb.best_monthly_price <= (req->>'value')::numeric then true
                           when req->>'operator' = 'gte' and vmb.best_monthly_price >= (req->>'value')::numeric then true
                           else false
                       end
                   when req->>'feature_key' in ('duration_months', 'annual_mileage', 'margin_pct') then true
                   when req->>'operator' = 'eq' and req->>'value' = 'true' and vfs.resolved_value_bool = true then true
                   when req->>'operator' = 'eq' and req->>'value' = 'false' and (coalesce(vfs.resolved_value_bool, false) = false) then true
                   when req->>'operator' = 'eq' and vfs.resolved_value_text = req->>'value' then true
                   when req->>'operator' = 'gte' and vfs.resolved_value_num >= (req->>'value')::numeric then true
                   when req->>'operator' = 'lte' and vfs.resolved_value_num <= (req->>'value')::numeric then true
                   when req->>'operator' = 'in' and (req->'values') @> to_jsonb(vfs.resolved_value_text) then true
                   else false
               end as is_match
        from target_vehicles tv
        cross join jsonb_array_elements(p_requirements) as req
        left join reverse_search.vehicle_features_summary_view vfs 
               on vfs.source_vehicle_id = tv.v_id 
              and vfs.feature_key = req->>'feature_key'
              and req->>'feature_key' not in ('monthly_price_net', 'duration_months', 'annual_mileage', 'margin_pct')
        left join vehicle_matrix_best vmb on vmb.v_id = tv.v_id
    ),
    failed_must_haves as (
        select distinct v_id
        from vehicle_evals
        where requirement = 'MUST_HAVE' and is_match = false
    ),
    survivors as (
        select ve.v_id, ve.brand, ve.model, ve.version,
               min(ve.best_monthly_price) as final_price,
               sum(case when is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net') then weight else 0 end) as score,
               jsonb_agg(feature_key) filter (where is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net')) as matched,
               jsonb_agg(feature_key) filter (where not is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net')) as missing
        from vehicle_evals ve
        where ve.v_id not in (select v_id from failed_must_haves)
        group by ve.v_id, ve.brand, ve.model, ve.version
    )
    select s.v_id as vehicle_id, s.brand, s.model, s.version,
           round((s.score / v_total_possible_score) * 100, 2) as match_score_pct,
           coalesce(s.matched, '[]'::jsonb) as matched_features,
           coalesce(s.missing, '[]'::jsonb) as missing_features,
           s.final_price as best_monthly_price
    from survivors s
    order by match_score_pct desc, s.brand, s.model
    limit 200;

end;
$function$;

CREATE OR REPLACE FUNCTION public.rpc_reverse_search(
    p_requirements jsonb,
    p_brands text[] DEFAULT NULL,
    p_models text[] DEFAULT NULL,
    p_samar_class_ids int[] DEFAULT NULL
)
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, match_score_pct numeric, matched_features jsonb, missing_features jsonb, best_monthly_price numeric)
 LANGUAGE sql
AS $function$
    select * from reverse_search.rpc_reverse_search(p_requirements, p_brands, p_models, p_samar_class_ids);
$function$;


-- ==========================================
-- 2. rpc_get_available_filters
-- ==========================================
CREATE OR REPLACE FUNCTION reverse_search.rpc_get_available_filters(
    p_brands text[] DEFAULT NULL,
    p_models text[] DEFAULT NULL,
    p_samar_class_ids int[] DEFAULT NULL,
    p_current_filters jsonb DEFAULT '{}'::jsonb
)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
declare
    v_result jsonb;
begin
    with filtered_vehicles as (
        select vs.id
        from public.vehicle_synthesis vs
        left join public.samar_classes sc on sc.id = (vs.synthesis_data->>'samar_class_id')::int
        where 
            (p_brands is null or array_length(p_brands, 1) is null or lower(vs.synthesis_data->>'brand') = any(select lower(unnest) from unnest(p_brands)))
            and (p_models is null or array_length(p_models, 1) is null or lower(vs.synthesis_data->>'model') = any(select lower(unnest) from unnest(p_models)))
            and (p_samar_class_ids is null or array_length(p_samar_class_ids, 1) is null or sc.id = any(p_samar_class_ids))
    ),
    features as (
        select vfs.*
        from reverse_search.vehicle_features_summary_view vfs
        join filtered_vehicles fv on fv.id = vfs.source_vehicle_id
        where vfs.is_filterable = true
    ),
    enum_facets as (
        select 
            facet_group_key as group_name,
            feature_key,
            display_name as feature_name,
            parent_feature_key,
            facet_level,
            is_primary_facet,
            jsonb_agg(jsonb_build_object('value', resolved_value_text, 'count', cnt)) as items
        from (
            select coalesce(facet_group_key, category_name) as facet_group_key, parent_feature_key, facet_level, is_primary_facet, feature_key, display_name, resolved_value_text, count(distinct source_vehicle_id) as cnt
            from features
            where feature_type in ('enum', 'text') and (is_range_filter is null or is_range_filter = false)
            group by coalesce(facet_group_key, category_name), parent_feature_key, facet_level, is_primary_facet, feature_key, display_name, resolved_value_text
            having count(distinct source_vehicle_id) > 0 and resolved_value_text is not null
        ) t
        group by facet_group_key, feature_key, display_name, parent_feature_key, facet_level, is_primary_facet
    ),
    range_facets as (
        select 
            coalesce(facet_group_key, category_name) as group_name,
            feature_key,
            display_name as feature_name,
            parent_feature_key,
            facet_level,
            is_primary_facet,
            min(resolved_value_num) as min_val,
            max(resolved_value_num) as max_val
        from features
        where (feature_type = 'numeric' or is_range_filter = true) and resolved_value_num is not null
        group by coalesce(facet_group_key, category_name), feature_key, display_name, parent_feature_key, facet_level, is_primary_facet
    ),
    bool_facets as (
        select 
            coalesce(facet_group_key, category_name) as group_name,
            feature_key,
            display_name as feature_name,
            parent_feature_key,
            facet_level,
            is_primary_facet,
            count(distinct source_vehicle_id) as cnt
        from features
        where feature_type = 'boolean' and resolved_value_bool = true and (is_range_filter is null or is_range_filter = false)
        group by coalesce(facet_group_key, category_name), feature_key, display_name, parent_feature_key, facet_level, is_primary_facet
        having count(distinct source_vehicle_id) > 0
    )
    select jsonb_build_object(
        'filters_provided', (p_brands is not null or p_models is not null or p_samar_class_ids is not null),
        'facet_groups', (
            select coalesce(jsonb_agg(jsonb_build_object(
                'group_name', group_name,
                'filters', filters
            )), '[]'::jsonb)
            from (
                select group_name, jsonb_agg(jsonb_build_object(
                    'key', feature_key,
                    'name', feature_name,
                    'type', 'enum',
                    'parent', parent_feature_key,
                    'level', facet_level,
                    'primary', coalesce(is_primary_facet, false),
                    'items', items
                ) order by coalesce(facet_level, 0), feature_name) as filters
                from enum_facets
                group by group_name
            ) fg
        ),
        'range_filters', (select coalesce(jsonb_agg(row_to_json(rf)), '[]'::jsonb) from range_facets rf),
        'boolean_filters', (select coalesce(jsonb_agg(row_to_json(bf)), '[]'::jsonb) from bool_facets bf)
    ) into v_result;

    return coalesce(v_result, '{}'::jsonb);
end;
$function$;

CREATE OR REPLACE FUNCTION public.rpc_get_available_filters(
    p_brands text[] DEFAULT NULL,
    p_models text[] DEFAULT NULL,
    p_samar_class_ids int[] DEFAULT NULL,
    p_current_filters jsonb DEFAULT '{}'::jsonb
)
 RETURNS jsonb
 LANGUAGE sql
AS $function$
    select reverse_search.rpc_get_available_filters(p_brands, p_models, p_samar_class_ids, p_current_filters);
$function$;
