-- Migration: 20260318210000_fix_body_types_available_filters.sql
-- Description: Fix the body_types filter in rpc_get_available_filters to correctly join on vehicle_feature_state instead of mapped_ai_data

CREATE OR REPLACE FUNCTION public.rpc_get_available_filters(p_brands text[] DEFAULT NULL::text[], p_models text[] DEFAULT NULL::text[], p_body_types text[] DEFAULT NULL::text[], p_samar_class_ids integer[] DEFAULT NULL::integer[], p_current_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE sql
 SET search_path TO ''
AS $function$
    select reverse_search.rpc_get_available_filters(p_brands, p_models, p_body_types, p_samar_class_ids, p_current_filters);
$function$;

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_available_filters(p_brands text[] DEFAULT NULL::text[], p_models text[] DEFAULT NULL::text[], p_body_types text[] DEFAULT NULL::text[], p_samar_class_ids integer[] DEFAULT NULL::integer[], p_current_filters jsonb DEFAULT '{}'::jsonb)
 RETURNS jsonb
 LANGUAGE plpgsql
 SET search_path TO ''
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
            and (p_body_types is null or array_length(p_body_types, 1) is null or vs.id in (
                select vfs.source_vehicle_id 
                from reverse_search.vehicle_feature_state vfs
                join reverse_search.universal_features uf on uf.id = vfs.feature_id
                where uf.feature_key = 'body_style' 
                  and lower(vfs.resolved_value_text) = any(select lower(unnest) from unnest(p_body_types))
            ))
            and (p_samar_class_ids is null or array_length(p_samar_class_ids, 1) is null or sc.id = any(p_samar_class_ids))
    ),
    features as materialized (
        select 
            vfs.source_vehicle_id,
            uf.feature_key,
            uf.display_name,
            ufc.display_name as category_name,
            uf.feature_type,
            vfs.resolved_value_bool,
            vfs.resolved_value_num,
            vfs.resolved_value_text,
            uf.is_filterable,
            uf.facet_group_key,
            uf.parent_feature_key,
            uf.facet_level,
            uf.is_primary_facet,
            uf.is_range_filter
        from reverse_search.vehicle_feature_state vfs
        join reverse_search.universal_features uf 
            on uf.id = vfs.feature_id 
            and uf.is_active = true
            and uf.is_filterable = true
        join reverse_search.universal_feature_categories ufc 
            on ufc.id = uf.category_id
        where vfs.source_vehicle_id in (select id from filtered_vehicles)
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
        'filters_provided', (p_brands is not null or p_models is not null or p_body_types is not null or p_samar_class_ids is not null),
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
