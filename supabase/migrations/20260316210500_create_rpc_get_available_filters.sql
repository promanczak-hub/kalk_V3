-- =============================================================
-- Migration: Create rpc_get_available_filters
-- ISOLATION: reverse_search schema
-- =============================================================

create or replace function reverse_search.rpc_get_available_filters(p_segment text, p_current_filters jsonb default '{}'::jsonb)
returns jsonb language plpgsql as $$
declare
    v_result jsonb;
begin
    -- MVP: aggregations for all vehicles in the given segment
    
    with filtered_vehicles as (
        select vs.id
        from public.vehicle_synthesis vs
        left join public.samar_classes sc on sc.id = (vs.synthesis_data->>'samar_class_id')::int
        where lower(sc.category) = lower(p_segment)
    ),
    features as (
        select vfs.*
        from reverse_search.vehicle_features_summary_view vfs
        join filtered_vehicles fv on fv.id = vfs.source_vehicle_id
        where vfs.is_filterable = true
    ),
    enum_facets as (
        select 
            group_name as group_name,
            feature_key,
            display_name as feature_name,
            jsonb_agg(jsonb_build_object('value', resolved_value_text, 'count', cnt)) as items
        from (
            select group_name, feature_key, display_name, resolved_value_text, count(distinct source_vehicle_id) as cnt
            from features
            where feature_type in ('enum', 'text')
            group by group_name, feature_key, display_name, resolved_value_text
            having count(distinct source_vehicle_id) > 0 and resolved_value_text is not null
        ) t
        group by group_name, feature_key, display_name
    ),
    range_facets as (
        select 
            feature_key,
            display_name as feature_name,
            min(resolved_value_num) as min_val,
            max(resolved_value_num) as max_val
        from features
        where feature_type = 'numeric' and resolved_value_num is not null
        group by feature_key, display_name
    ),
    bool_facets as (
        select 
            feature_key,
            display_name as feature_name,
            count(distinct source_vehicle_id) as cnt
        from features
        where feature_type = 'boolean' and resolved_value_bool = true
        group by feature_key, display_name
        having count(distinct source_vehicle_id) > 0
    )
    select jsonb_build_object(
        'segment', p_segment,
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
                    'items', items
                )) as filters
                from enum_facets
                group by group_name
            ) fg
        ),
        'range_filters', (select coalesce(jsonb_agg(row_to_json(rf)), '[]'::jsonb) from range_facets rf),
        'boolean_filters', (select coalesce(jsonb_agg(row_to_json(bf)), '[]'::jsonb) from bool_facets bf)
    ) into v_result;

    return coalesce(v_result, '{}'::jsonb);
end;
$$;
