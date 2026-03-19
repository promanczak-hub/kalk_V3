-- Migration: 20260318183000_update_available_filters_strict.sql
-- Description: Update rpc_get_available_filters to accurately calculate facet counts by taking into account p_current_filters.

CREATE OR REPLACE FUNCTION reverse_search.rpc_get_available_filters(
    p_segment text DEFAULT NULL,
    p_brands text[] DEFAULT NULL,
    p_models text[] DEFAULT NULL,
    p_samar_class_ids int[] DEFAULT NULL,
    p_body_types text[] DEFAULT NULL,
    p_current_filters jsonb DEFAULT '{}'
)
RETURNS TABLE (
    feature_key text,
    feature_value text,
    cnt int
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    with filtered_vehicles as (
        select vs.id
        from public.vehicle_synthesis vs
        left join public.samar_classes sc on sc.id = (vs.synthesis_data->>'samar_class_id')::int
        where 
            (p_brands is null or array_length(p_brands, 1) is null or lower(vs.synthesis_data->>'brand') = any(select lower(unnest) from unnest(p_brands)))
            and (p_models is null or array_length(p_models, 1) is null or lower(vs.synthesis_data->>'model') = any(select lower(unnest) from unnest(p_models)))
            and (p_samar_class_ids is null or array_length(p_samar_class_ids, 1) is null or sc.id = any(p_samar_class_ids))
            and (p_body_types is null or array_length(p_body_types, 1) is null or lower(vs.synthesis_data->>'body_type') = any(select lower(unnest) from unnest(p_body_types)))
            
            -- Dynamic strict filtering based on p_current_filters
            AND (
                p_current_filters IS NULL OR 
                p_current_filters = '{}'::jsonb OR 
                NOT EXISTS (
                    SELECT 1
                    FROM jsonb_each(p_current_filters) AS cf(key, values)
                    WHERE 
                        jsonb_typeof(cf.values) = 'array' 
                        AND jsonb_array_length(cf.values) > 0
                        AND NOT EXISTS (
                            -- Check if vehicle has this feature matching one of the values
                            SELECT 1
                            FROM jsonb_array_elements(vs.synthesis_data->'features') as vf
                            WHERE 
                                vf->>'key' = cf.key AND
                                (
                                    vf->>'value_text' IN (SELECT jsonb_array_elements_text(cf.values))
                                    OR (vf->>'value_bool')::text IN (SELECT jsonb_array_elements_text(cf.values))
                                    OR (vf->>'value_num')::text IN (SELECT jsonb_array_elements_text(cf.values))
                                )
                        )
                )
            )
    ),
    feature_counts as (
        select 
            f->>'key' as f_key,
            coalesce(f->>'value_text', (f->>'value_bool')::text, (f->>'value_num')::text) as f_value,
            count(distinct vs.id) as f_cnt
        from public.vehicle_synthesis vs
        join filtered_vehicles fv on fv.id = vs.id
        cross join jsonb_array_elements(vs.synthesis_data->'features') as f
        group by 1, 2
    )
    select 
        f_key,
        f_value,
        f_cnt::int
    from feature_counts
    where f_cnt > 0;
END;
$$;
