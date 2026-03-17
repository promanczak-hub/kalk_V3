-- =============================================================
-- Migration: Update RPC reverse_search to support range filters
-- for duration_months and annual_mileage (gte/lte operators)
-- ISOLATION: public / reverse_search schema
-- =============================================================

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
            -- Range support: extract gte/lte bounds for duration and mileage
            max(case when req->>'feature_key' = 'duration_months' and req->>'operator' = 'gte' then (req->>'value')::numeric else null end) as req_duration_min,
            max(case when req->>'feature_key' = 'duration_months' and req->>'operator' = 'lte' then (req->>'value')::numeric else null end) as req_duration_max,
            -- Backward compat: single eq value
            max(case when req->>'feature_key' = 'duration_months' and req->>'operator' = 'eq' then (req->>'value')::numeric else null end) as req_duration_eq,
            max(case when req->>'feature_key' = 'annual_mileage' and req->>'operator' = 'gte' then (req->>'value')::numeric else null end) as req_mileage_min,
            max(case when req->>'feature_key' = 'annual_mileage' and req->>'operator' = 'lte' then (req->>'value')::numeric else null end) as req_mileage_max,
            -- Backward compat: single eq value
            max(case when req->>'feature_key' = 'annual_mileage' and req->>'operator' = 'eq' then (req->>'value')::numeric else null end) as req_mileage_eq,
            max(case when req->>'feature_key' = 'margin_pct' then (req->>'value')::numeric else null end) as req_margin
        from jsonb_array_elements(p_requirements) as req
    ),
    vehicle_matrix_best as (
        select vmc.vehicle_id as v_id, 
               min(vmc.monthly_price_net) as best_monthly_price
        from public.vehicle_matrix_cache vmc
        cross join matrix_context ctx
        where 
            -- Duration: range (gte/lte) OR exact (eq) OR no filter
            (
                (ctx.req_duration_min is not null and vmc.duration_months >= ctx.req_duration_min)
                or (ctx.req_duration_eq is not null and vmc.duration_months = ctx.req_duration_eq)
                or (ctx.req_duration_min is null and ctx.req_duration_eq is null)
            )
            and (
                (ctx.req_duration_max is not null and vmc.duration_months <= ctx.req_duration_max)
                or (ctx.req_duration_max is null and ctx.req_duration_eq is null)
                or (ctx.req_duration_eq is not null)
            )
            -- Mileage: range (gte/lte) OR exact (eq) OR no filter
            and (
                (ctx.req_mileage_min is not null and vmc.annual_mileage >= ctx.req_mileage_min)
                or (ctx.req_mileage_eq is not null and vmc.annual_mileage = ctx.req_mileage_eq)
                or (ctx.req_mileage_min is null and ctx.req_mileage_eq is null)
            )
            and (
                (ctx.req_mileage_max is not null and vmc.annual_mileage <= ctx.req_mileage_max)
                or (ctx.req_mileage_max is null and ctx.req_mileage_eq is null)
                or (ctx.req_mileage_eq is not null)
            )
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
                           when req->>'operator' = 'lte' and vmb.best_monthly_price <= (req->>'value')::numeric * 1.05 then true
                           when req->>'operator' = 'gte' and vmb.best_monthly_price >= (req->>'value')::numeric * 0.95 then true
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
