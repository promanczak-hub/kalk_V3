-- =============================================================
-- Migration: Create derived features
-- ISOLATION: reverse_search schema
-- =============================================================

create table if not exists reverse_search.derived_feature_rules (
    id uuid primary key default gen_random_uuid(),
    target_feature_id uuid not null references reverse_search.universal_features(id) on delete cascade,
    rule_type text not null check (rule_type in ('threshold', 'enum_match', 'text_match', 'boolean_match', 'json_logic')),
    rule_config jsonb not null,
    default_weight numeric not null default 1.0,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_derived_feature_rules_target
    on reverse_search.derived_feature_rules(target_feature_id) where is_active = true;

drop trigger if exists trg_derived_feature_rules_updated_at on reverse_search.derived_feature_rules;
create trigger trg_derived_feature_rules_updated_at
before update on reverse_search.derived_feature_rules
for each row execute function reverse_search.set_updated_at();

create or replace function reverse_search.rpc_refresh_vehicle_features(p_vehicle_id uuid, p_bundle_id uuid default null)
returns void language plpgsql as $$
declare
    v_rule record;
    v_source_state record;
    v_new_bool boolean;
    v_new_status text;
begin
    for v_rule in select d.*, u_target.feature_key as target_key, u_target.feature_type as target_type
                  from reverse_search.derived_feature_rules d
                  join reverse_search.universal_features u_target on u_target.id = d.target_feature_id
                  where d.is_active = true
    loop
        v_new_bool := false;
        v_new_status := 'unknown';

        if v_rule.rule_type in ('threshold', 'enum_match', 'text_match', 'boolean_match') then
            -- Fetch single source feature
            select vfs.* into v_source_state
            from reverse_search.vehicle_feature_state vfs
            join reverse_search.universal_features uf on uf.id = vfs.feature_id
            where uf.feature_key = v_rule.rule_config->>'source_feature_key'
              and vfs.source_vehicle_id = p_vehicle_id
              and (p_bundle_id is null or vfs.bundle_id = p_bundle_id)
            limit 1;

            if found then
                if v_rule.rule_type = 'threshold' and v_source_state.resolved_value_num is not null then
                    if v_rule.rule_config->>'operator' = 'lte' and v_source_state.resolved_value_num <= (v_rule.rule_config->>'value')::numeric then
                        v_new_bool := true;
                    elsif v_rule.rule_config->>'operator' = 'gte' and v_source_state.resolved_value_num >= (v_rule.rule_config->>'value')::numeric then
                        v_new_bool := true;
                    end if;
                elsif v_rule.rule_type = 'enum_match' and v_source_state.resolved_value_text is not null then
                    if v_rule.rule_config->>'operator' = 'in' and (v_rule.rule_config->'values') @> to_jsonb(v_source_state.resolved_value_text) then
                        v_new_bool := true;
                    elsif v_rule.rule_config->>'operator' = 'eq' and v_source_state.resolved_value_text = v_rule.rule_config->>'value' then
                        v_new_bool := true;
                    end if;
                elsif v_rule.rule_type = 'boolean_match' and v_source_state.resolved_value_bool is not null then
                    if v_rule.rule_config->>'operator' = 'eq' and v_source_state.resolved_value_bool = (v_rule.rule_config->>'value')::boolean then
                        v_new_bool := true;
                    end if;
                end if;
            end if;
        end if;

        if v_new_bool then
            v_new_status := 'present_inferred';
        end if;

        -- Upsert only if we inferred a positive boolean value (for now restricting derived rules to producing boolean flags like is_refrigerated)
        if v_rule.target_type = 'boolean' and v_new_bool = true then
            insert into reverse_search.vehicle_feature_state (
                source_vehicle_id, bundle_id, feature_id, resolved_status, resolved_value_bool,
                confidence, resolution_source, is_manual_override
            ) values (
                p_vehicle_id, p_bundle_id, v_rule.target_feature_id, v_new_status, v_new_bool,
                1.0, 'derived_rule', false
            )
            on conflict (source_vehicle_id, feature_id, coalesce(bundle_id, '00000000-0000-0000-0000-000000000000'::uuid))
            do update set
                resolved_status = excluded.resolved_status,
                resolved_value_bool = excluded.resolved_value_bool,
                resolution_source = excluded.resolution_source,
                updated_at = now()
            where reverse_search.vehicle_feature_state.is_manual_override = false;
        end if;
    end loop;
end;
$$;
