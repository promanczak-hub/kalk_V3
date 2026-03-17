-- =============================================================
-- Migration: Create rpc_reverse_search
-- ISOLATION: reverse_search schema
-- =============================================================

create or replace function reverse_search.rpc_reverse_search(
    p_segment text,
    p_requirements jsonb -- [{ "feature_key": "payload_kg", "operator": "gte", "value": 1000, "requirement": "MUST_HAVE", "weight": 1 }]
)
returns table (
    vehicle_id uuid,
    brand text,
    model text,
    version text,
    match_score_pct numeric,
    matched_features jsonb,
    missing_features jsonb
) language plpgsql as $$
declare
    v_total_possible_score numeric := 0;
begin
    -- 1. Oblicz maksymalną sumę punktów (dla NICE_TO_HAVE i ew. MUST_HAVE jeśli punktujemy wszystko)
    select coalesce(sum((r->>'weight')::numeric), 0) into v_total_possible_score
    from jsonb_array_elements(p_requirements) as r;

    if v_total_possible_score = 0 then
        v_total_possible_score := 1; -- avoid division by zero
    end if;

    return query
    with target_vehicles as (
        select vs.id as vehicle_id,
               vs.brand,
               vs.model,
               vs.synthesis_data->>'version' as version
        from public.vehicle_synthesis vs
        left join public.samar_classes sc on sc.id = (vs.synthesis_data->>'samar_class_id')::int
        where lower(sc.category) = lower(p_segment)
    ),
    vehicle_evals as (
        select tv.vehicle_id, tv.brand, tv.model, tv.version,
               req->>'feature_key' as feature_key,
               req->>'requirement' as requirement,
               (req->>'weight')::numeric as weight,
               vfs.resolved_value_bool,
               vfs.resolved_value_num,
               vfs.resolved_value_text,
               -- ewaluacja warunku
               case 
                   when req->>'operator' = 'eq' and req->>'value' = 'true' and vfs.resolved_value_bool = true then true
                   when req->>'operator' = 'eq' and req->>'value' = 'false' and (vfs.resolved_value_bool = false or vfs.resolved_value_bool is null) then true
                   when req->>'operator' = 'eq' and vfs.resolved_value_text = req->>'value' then true
                   when req->>'operator' = 'gte' and vfs.resolved_value_num >= (req->>'value')::numeric then true
                   when req->>'operator' = 'lte' and vfs.resolved_value_num <= (req->>'value')::numeric then true
                   when req->>'operator' = 'in' and (req->'values') @> to_jsonb(vfs.resolved_value_text) then true
                   else false
               end as is_match
        from target_vehicles tv
        cross join jsonb_array_elements(p_requirements) as req
        left join reverse_search.vehicle_features_summary_view vfs 
               on vfs.source_vehicle_id = tv.vehicle_id 
              and vfs.feature_key = req->>'feature_key'
    ),
    -- Twardy odrzut MUST_HAVE
    failed_must_haves as (
        select distinct vehicle_id
        from vehicle_evals
        where requirement = 'MUST_HAVE' and is_match = false
    ),
    -- Agregacja dla tych co przetrwali
    survivors as (
        select ve.vehicle_id, ve.brand, ve.model, ve.version,
               sum(case when is_match then weight else 0 end) as score,
               jsonb_agg(feature_key) filter (where is_match) as matched,
               jsonb_agg(feature_key) filter (where not is_match) as missing
        from vehicle_evals ve
        where ve.vehicle_id not in (select vehicle_id from failed_must_haves)
        group by ve.vehicle_id, ve.brand, ve.model, ve.version
    )
    select s.vehicle_id, s.brand, s.model, s.version,
           round((s.score / v_total_possible_score) * 100, 2) as match_score_pct,
           coalesce(s.matched, '[]'::jsonb) as matched_features,
           coalesce(s.missing, '[]'::jsonb) as missing_features
    from survivors s
    order by match_score_pct desc, s.brand, s.model;

end;
$$;
