-- =============================================================
-- Migration: Update rpc_reverse_search to support Matrix Caching
-- =============================================================

create or replace function reverse_search.rpc_reverse_search(
    p_segment text,
    p_requirements jsonb -- [{ "feature_key": "monthly_price_net", "operator": "lte", "value": 1500, "requirement": "MUST_HAVE", "weight": 1 }]
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
    -- Wykluczamy punktację za sztuczne filtry kontekstowe (duration_months, annual_mileage, margin_pct)
    select coalesce(sum((r->>'weight')::numeric), 0) into v_total_possible_score
    from jsonb_array_elements(p_requirements) as r
    where r->>'feature_key' not in ('duration_months', 'annual_mileage', 'margin_pct');

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
    -- Wyciągnięcie parametrów cenowych z wymagań (żeby ograniczyć złączenia z cennikiem)
    matrix_context as (
        select 
            max(case when req->>'feature_key' = 'duration_months' then (req->>'value')::numeric else null end) as req_duration,
            max(case when req->>'feature_key' = 'annual_mileage' then (req->>'value')::numeric else null end) as req_mileage,
            max(case when req->>'feature_key' = 'margin_pct' then (req->>'value')::numeric else null end) as req_margin
        from jsonb_array_elements(p_requirements) as req
    ),
    -- Znajdź NAJLEPSZĄ kwotę (najniższą) dla każdego auta w zadanym kontekście
    vehicle_matrix_best as (
        select vmc.vehicle_id, 
               min(vmc.monthly_price_net) as best_monthly_price
        from public.vehicle_matrix_cache vmc
        cross join matrix_context ctx
        where (ctx.req_duration is null or vmc.duration_months = ctx.req_duration)
          and (ctx.req_mileage is null or vmc.annual_mileage = ctx.req_mileage)
          and (ctx.req_margin is null or vmc.margin_pct >= ctx.req_margin)
        group by vmc.vehicle_id
    ),
    vehicle_evals as (
        select tv.vehicle_id, tv.brand, tv.model, tv.version,
               req->>'feature_key' as feature_key,
               req->>'requirement' as requirement,
               (req->>'weight')::numeric as weight,
               vfs.resolved_value_bool,
               vfs.resolved_value_num,
               vfs.resolved_value_text,
               vmb.best_monthly_price,
               -- ewaluacja warunku
               case 
                   -- Specjalna obsługa dla cech finansowych
                   when req->>'feature_key' = 'monthly_price_net' and req->>'operator' = 'lte' and vmb.best_monthly_price <= (req->>'value')::numeric then true
                   when req->>'feature_key' = 'monthly_price_net' and req->>'operator' = 'gte' and vmb.best_monthly_price >= (req->>'value')::numeric then true
                   -- Cechy kontekstowe uznajemy zawsze za dopasowane, by nie psuły wyników (są aplikowane w CTE wyżej)
                   when req->>'feature_key' in ('duration_months', 'annual_mileage', 'margin_pct') then true
                   
                   -- Zwykłe cechy
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
               on vfs.source_vehicle_id = tv.vehicle_id 
              and vfs.feature_key = req->>'feature_key'
              and req->>'feature_key' not in ('monthly_price_net', 'duration_months', 'annual_mileage', 'margin_pct')
        left join vehicle_matrix_best vmb on vmb.vehicle_id = tv.vehicle_id
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
               sum(case when is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct') then weight else 0 end) as score,
               jsonb_agg(feature_key) filter (where is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct')) as matched,
               jsonb_agg(feature_key) filter (where not is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct')) as missing
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
