CREATE OR REPLACE FUNCTION reverse_search.rpc_reverse_search(p_requirements jsonb, p_brands text[] DEFAULT NULL::text[], p_models text[] DEFAULT NULL::text[], p_samar_class_ids integer[] DEFAULT NULL::integer[], p_trims text[] DEFAULT NULL::text[])
 RETURNS TABLE(vehicle_id uuid, brand text, model text, version text, match_score_pct numeric, matched_features jsonb, missing_features jsonb, best_monthly_price numeric, fuel_type text, power_hp integer, transmission text, body_style text, drive_type text, base_price_gross text, options_price_gross text, total_price_gross text, suggested_discount_pct numeric, trim_level text, vehicle_class text, has_ltr_cache boolean, service_cost_type text, tire_class text, offer_number text, configuration_code text)
 LANGUAGE plpgsql
AS $function$
declare
    v_total_possible_score numeric := 0;
begin
    select coalesce(sum((r->>'weight')::numeric), 0) into v_total_possible_score
    from jsonb_array_elements(
        case when jsonb_array_length(coalesce(p_requirements, '[]'::jsonb)) > 0 
             then p_requirements 
             else '[{"feature_key": "dummy"}]'::jsonb 
        end
    ) as r
    where r->>'feature_key' not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net', 'dummy');

    if v_total_possible_score = 0 then
        v_total_possible_score := 1;
    end if;

    return query
    with target_vehicles as (
        select vs.id as v_id,
               vs.brand,
               vs.model,
               vs.synthesis_data->>'version' as version,
               vs.offer_number,
               vs.synthesis_data->>'configuration_code' as configuration_code,
               -- card_summary fields
               (vs.synthesis_data->'card_summary'->>'fuel') as cs_fuel,
               (vs.synthesis_data->'card_summary'->>'power_hp')::int as cs_power_hp,
               (vs.synthesis_data->'card_summary'->>'transmission') as cs_transmission,
               (vs.synthesis_data->'card_summary'->>'body_style') as cs_body_style,
               (vs.synthesis_data->'card_summary'->>'drive_type') as cs_drive_type,
               (vs.synthesis_data->'card_summary'->>'base_price') as cs_base_price,
               (vs.synthesis_data->'card_summary'->>'options_price') as cs_options_price,
               (vs.synthesis_data->'card_summary'->>'total_price') as cs_total_price,
               (vs.synthesis_data->'card_summary'->>'suggested_discount_pct')::numeric as cs_discount,
               (vs.synthesis_data->'card_summary'->>'trim_level') as cs_trim_level,
               (vs.synthesis_data->'card_summary'->>'vehicle_class') as cs_vehicle_class,
               coalesce(vs.synthesis_data->'card_summary'->'standard_equipment', '[]'::jsonb) as cs_std_equipment,
               coalesce(vs.synthesis_data->'card_summary'->'paid_options', '[]'::jsonb) as cs_paid_options,
               -- calculator_setup fields
               (vs.synthesis_data->'calculator_setup'->>'service_cost_type') as cs_service_type,
               (vs.synthesis_data->'calculator_setup'->'tire_params'->>'tire_class') as cs_tire_class
        from public.vehicle_synthesis vs
        left join public.samar_classes sc on sc.id = (vs.synthesis_data->>'samar_class_id')::int
        where 
            (p_brands is null or array_length(p_brands, 1) is null or lower(vs.synthesis_data->>'brand') = any(select lower(unnest) from unnest(p_brands)))
            and (p_models is null or array_length(p_models, 1) is null or lower(vs.synthesis_data->>'model') = any(select lower(unnest) from unnest(p_models)))
            and (p_samar_class_ids is null or array_length(p_samar_class_ids, 1) is null or sc.id = any(p_samar_class_ids))
            and (p_trims is null or array_length(p_trims, 1) is null or lower(vs.synthesis_data->'card_summary'->>'trim_level') = any(select lower(unnest) from unnest(p_trims)))
    ),
    matrix_context as (
        select 
            max(case when req->>'feature_key' = 'duration_months' and req->>'operator' = 'gte' then (req->>'value')::numeric else null end) as req_duration_min,
            max(case when req->>'feature_key' = 'duration_months' and req->>'operator' = 'lte' then (req->>'value')::numeric else null end) as req_duration_max,
            max(case when req->>'feature_key' = 'duration_months' and req->>'operator' = 'eq' then (req->>'value')::numeric else null end) as req_duration_eq,
            max(case when req->>'feature_key' = 'annual_mileage' and req->>'operator' = 'gte' then (req->>'value')::numeric else null end) as req_mileage_min,
            max(case when req->>'feature_key' = 'annual_mileage' and req->>'operator' = 'lte' then (req->>'value')::numeric else null end) as req_mileage_max,
            max(case when req->>'feature_key' = 'annual_mileage' and req->>'operator' = 'eq' then (req->>'value')::numeric else null end) as req_mileage_eq,
            max(case when req->>'feature_key' = 'margin_pct' then (req->>'value')::numeric else null end) as req_margin_pct
        from jsonb_array_elements(
            case when jsonb_array_length(coalesce(p_requirements, '[]'::jsonb)) > 0 
                 then p_requirements 
                 else '[{"feature_key": "dummy"}]'::jsonb 
            end
        ) as req
    ),
    vehicle_matrix_best as (
        -- Dynamic margin: read 0% cost, apply margin formula: cost / (1 - margin/100)
        select vmc.vehicle_id as v_id,
               round(
                 min(vmc.monthly_price_net) / (1.0 - coalesce(ctx.req_margin_pct, 0) / 100.0),
                 0
               ) as best_monthly_price,
               true as has_cache
        from public.vehicle_matrix_cache vmc
        cross join matrix_context ctx
        where vmc.margin_pct = 0
            and (
                (ctx.req_duration_min is not null and vmc.duration_months >= ctx.req_duration_min)
                or (ctx.req_duration_eq is not null and vmc.duration_months = ctx.req_duration_eq)
                or (ctx.req_duration_min is null and ctx.req_duration_eq is null)
            )
            and (
                (ctx.req_duration_max is not null and vmc.duration_months <= ctx.req_duration_max)
                or (ctx.req_duration_max is null and ctx.req_duration_eq is null)
                or (ctx.req_duration_eq is not null)
            )
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
        group by vmc.vehicle_id, ctx.req_margin_pct
    ),
    vehicle_evals as (
        select tv.v_id, tv.brand, tv.model, tv.version,
               tv.offer_number, tv.configuration_code,
               tv.cs_fuel, tv.cs_power_hp, tv.cs_transmission, tv.cs_body_style, tv.cs_drive_type,
               tv.cs_base_price, tv.cs_options_price, tv.cs_total_price, tv.cs_discount,
               tv.cs_trim_level, tv.cs_vehicle_class, tv.cs_service_type, tv.cs_tire_class,
               req->>'feature_key' as feature_key,
               req->>'requirement' as requirement,
               (req->>'weight')::numeric as weight,
               vfs.resolved_value_bool,
               vfs.resolved_value_num,
               vfs.resolved_value_text,
               vmb.best_monthly_price,
               coalesce(vmb.has_cache, false) as has_cache,
               case 
                   when req->>'feature_key' = 'dummy' then true
                   when req->>'feature_key' = 'monthly_price_net' then
                       case 
                           when req->>'operator' = 'lte' and vmb.best_monthly_price <= (req->>'value')::numeric * 1.05 then true
                           when req->>'operator' = 'gte' and vmb.best_monthly_price >= (req->>'value')::numeric * 0.95 then true
                           else false
                       end
                   when req->>'feature_key' in ('duration_months', 'annual_mileage', 'margin_pct') then true
                   when req->>'feature_key' like 'opt_std:%' then
                       (tv.cs_std_equipment @> jsonb_build_array(substring(req->>'feature_key' from 9)))
                   when req->>'feature_key' like 'opt_paid:%' then
                       (tv.cs_paid_options @> jsonb_build_array(jsonb_build_object('name', substring(req->>'feature_key' from 10))))
                   when req->>'operator' = 'eq' and req->>'value' = 'true' and vfs.resolved_value_bool = true then true
                   when req->>'operator' = 'eq' and req->>'value' = 'false' and (coalesce(vfs.resolved_value_bool, false) = false) then true
                   when req->>'operator' = 'eq' and vfs.resolved_value_text = req->>'value' then true
                   when req->>'operator' = 'gte' and vfs.resolved_value_num >= (req->>'value')::numeric then true
                   when req->>'operator' = 'lte' and vfs.resolved_value_num <= (req->>'value')::numeric then true
                   when req->>'operator' = 'in' and (req->'values') @> to_jsonb(vfs.resolved_value_text) then true
                   else false
               end as is_match
        from target_vehicles tv
        left join jsonb_array_elements(
            case when jsonb_array_length(coalesce(p_requirements, '[]'::jsonb)) > 0 
                 then p_requirements 
                 else '[{"feature_key": "dummy"}]'::jsonb 
            end
        ) as req on true
        left join reverse_search.vehicle_features_summary_view vfs 
               on vfs.source_vehicle_id = tv.v_id 
              and vfs.feature_key = req->>'feature_key'
              and req->>'feature_key' not in ('monthly_price_net', 'duration_months', 'annual_mileage', 'margin_pct', 'dummy')
        left join vehicle_matrix_best vmb on vmb.v_id = tv.v_id
    ),
    failed_must_haves as (
        select distinct v_id
        from vehicle_evals
        where requirement = 'MUST_HAVE' and is_match = false
    ),
    survivors as (
        select ve.v_id, ve.brand, ve.model, ve.version,
               ve.offer_number, ve.configuration_code,
               ve.cs_fuel, ve.cs_power_hp, ve.cs_transmission, ve.cs_body_style, ve.cs_drive_type,
               ve.cs_base_price, ve.cs_options_price, ve.cs_total_price, ve.cs_discount,
               ve.cs_trim_level, ve.cs_vehicle_class, ve.cs_service_type, ve.cs_tire_class,
               min(ve.best_monthly_price) as final_price,
               bool_or(ve.has_cache) as has_cache,
               sum(case when is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net', 'dummy') then weight else 0 end) as score,
               jsonb_agg(feature_key) filter (where is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net', 'dummy')) as matched,
               jsonb_agg(feature_key) filter (where not is_match and feature_key not in ('duration_months', 'annual_mileage', 'margin_pct', 'monthly_price_net', 'dummy')) as missing
        from vehicle_evals ve
        where ve.v_id not in (select v_id from failed_must_haves)
        group by ve.v_id, ve.brand, ve.model, ve.version,
                 ve.offer_number, ve.configuration_code,
                 ve.cs_fuel, ve.cs_power_hp, ve.cs_transmission, ve.cs_body_style, ve.cs_drive_type,
                 ve.cs_base_price, ve.cs_options_price, ve.cs_total_price, ve.cs_discount,
                 ve.cs_trim_level, ve.cs_vehicle_class, ve.cs_service_type, ve.cs_tire_class
    )
    select s.v_id as vehicle_id, s.brand, s.model, s.version,
           round((s.score / v_total_possible_score) * 100, 2) as match_score_pct,
           coalesce(s.matched, '[]'::jsonb) as matched_features,
           coalesce(s.missing, '[]'::jsonb) as missing_features,
           s.final_price as best_monthly_price,
           s.cs_fuel as fuel_type,
           s.cs_power_hp as power_hp,
           s.cs_transmission as transmission,
           s.cs_body_style as body_style,
           s.cs_drive_type as drive_type,
           s.cs_base_price as base_price_gross,
           s.cs_options_price as options_price_gross,
           s.cs_total_price as total_price_gross,
           s.cs_discount as suggested_discount_pct,
           s.cs_trim_level as trim_level,
           s.cs_vehicle_class as vehicle_class,
           s.has_cache as has_ltr_cache,
           s.cs_service_type as service_cost_type,
           s.cs_tire_class as tire_class,
           s.offer_number,
           s.configuration_code
    from survivors s
    order by match_score_pct desc, s.brand, s.model
    limit 200;

end;
$function$;
