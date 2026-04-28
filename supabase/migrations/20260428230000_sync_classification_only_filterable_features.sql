-- Restrict reverse_search.rpc_sync_classification_features to filterable features.
--
-- Background: this RPC populates vehicle_synthesis.feature_keys_present by
-- string-matching trigger_keywords + display_name tokens against the vehicle's
-- text fields. Previously it considered every is_active=true feature, so
-- deprecated naked variants (e.g. `abs` while `eq_abs` is canonical) kept
-- getting re-added on every UPDATE. Adding `is_filterable=true` to both UNION
-- branches matches what every consumer of feature_keys_present actually uses
-- (rpc_reverse_search, rpc_get_available_filters, rpc_search_vehicles_*).
--
-- Companion one-time cleanup: bulk-touch every vehicle to reclassify with the
-- new rule. See migration 20260428230100_bulk_reclassify_vehicles.sql.

CREATE OR REPLACE FUNCTION reverse_search.rpc_sync_classification_features(p_vehicle_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
    v_brand text;
    v_model text;
    v_sd jsonb;
    v_cs jsonb;
    v_mai jsonb;
    v_std jsonb;
    v_paid jsonb;
    v_svc jsonb;
    v_haystack text;
    v_matched text[];
begin
    select brand, model, coalesce(synthesis_data, '{}'::jsonb)
      into v_brand, v_model, v_sd
      from public.vehicle_synthesis
     where id = p_vehicle_id;

    if not found then
        return jsonb_build_object('error', 'vehicle_not_found', 'vehicle_id', p_vehicle_id);
    end if;

    v_cs  := coalesce(v_sd->'card_summary', '{}'::jsonb);
    v_mai := coalesce(v_sd->'mapped_ai_data', '{}'::jsonb);

    v_std  := case when jsonb_typeof(v_cs->'standard_equipment') = 'array'
                   then v_cs->'standard_equipment' else '[]'::jsonb end;
    v_paid := case when jsonb_typeof(v_cs->'paid_options') = 'array'
                   then v_cs->'paid_options' else '[]'::jsonb end;
    v_svc  := case when jsonb_typeof(v_cs->'service_equipment') = 'array'
                   then v_cs->'service_equipment' else '[]'::jsonb end;

    with parts as (
        select lower(coalesce(v_brand, '')) as p
        union all select lower(coalesce(v_model, ''))
        union all select lower(coalesce(v_cs->>'trim_level',          v_mai->>'trim_level',     ''))
        union all select lower(coalesce(v_cs->>'body_style',          v_mai->>'body_style',     ''))
        union all select lower(coalesce(v_cs->>'vehicle_class',       v_mai->>'vehicle_class',  ''))
        union all select lower(coalesce(v_cs->>'fuel',                v_mai->>'fuel',           ''))
        union all select lower(coalesce(v_cs->>'transmission',        v_mai->>'transmission',   ''))
        union all select lower(coalesce(v_cs->>'drive_type',          v_mai->>'drive_type',     ''))
        union all select lower(coalesce(v_cs->>'engine_designation',     ''))
        union all select lower(coalesce(v_cs->>'engine_marketing_name',  ''))
        union all select lower(coalesce(v_cs->>'powertrain',             ''))
        union all select lower(coalesce(v_mai->>'description',           ''))
        union all
        select lower(
            case jsonb_typeof(elem)
                when 'string' then elem #>> '{}'
                when 'object' then
                    coalesce(elem->>'name', '') || ' ' ||
                    coalesce((
                        select string_agg(
                            case jsonb_typeof(sub)
                                when 'string' then sub #>> '{}'
                                when 'object' then coalesce(sub->>'name', '')
                                else ''
                            end,
                            ' '
                        )
                        from jsonb_array_elements(
                            case when jsonb_typeof(elem->'items') = 'array'
                                 then elem->'items' else '[]'::jsonb end
                        ) sub
                    ), '')
                else ''
            end
        )
        from jsonb_array_elements(v_std) elem
        union all
        select lower(coalesce(elem->>'name', ''))
        from jsonb_array_elements(v_paid) elem
        union all
        select lower(coalesce(elem->>'name', ''))
        from jsonb_array_elements(v_svc) elem
    )
    select coalesce(string_agg(p, ' || '), '')
      into v_haystack
      from parts
     where p is not null and p <> '';

    with feature_terms as (
        select
            uf.feature_key,
            lower(trim(kw)) as term
          from reverse_search.universal_features uf,
               unnest(coalesce(uf.trigger_keywords, array[]::text[])) kw
         where uf.is_active = true
           and uf.is_filterable = true
           and kw is not null and length(trim(kw)) >= 3

        union all

        select
            uf.feature_key,
            (rm.match)[1] as term
          from reverse_search.universal_features uf
          cross join lateral (
              select match, row_number() over () as rn
                from regexp_matches(
                    lower(coalesce(uf.display_name, '')),
                    '\m[a-ząćęłńóśźż]{4,}\M',
                    'g'
                ) as match
          ) rm
         where uf.is_active = true
           and uf.is_filterable = true
           and rm.rn <= 3
    ),
    matched as (
        select distinct ft.feature_key
          from feature_terms ft
         where length(ft.term) >= 3
           and position(ft.term in v_haystack) > 0
    )
    select coalesce(array_agg(feature_key order by feature_key), array[]::text[])
      into v_matched
      from matched;

    update public.vehicle_synthesis
       set feature_keys_present = v_matched
     where id = p_vehicle_id;

    return jsonb_build_object(
        'vehicle_id',      p_vehicle_id,
        'matched_count',   coalesce(array_length(v_matched, 1), 0),
        'haystack_length', length(v_haystack)
    );
end;
$function$;
