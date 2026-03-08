-- =============================================================
-- Migration: Create reverse_search schema
-- Purpose: Universal features model, vehicle feature evidence,
--          vehicle feature state, context bundles, service options,
--          reverse discovery views, brochure views, card summary views.
-- ISOLATION: All objects in schema reverse_search.
--            No changes to public schema.
-- =============================================================

-- 1. Schema and extensions
create schema if not exists reverse_search;
create extension if not exists pgcrypto;

-- 2. Universal feature categories
create table if not exists reverse_search.universal_feature_categories (
    id uuid primary key default gen_random_uuid(),
    category_key text not null unique,
    display_name text not null,
    vehicle_scope text not null default 'both'
        check (vehicle_scope in ('passenger', 'commercial', 'both')),
    sort_order integer not null default 100,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_universal_feature_categories_scope
    on reverse_search.universal_feature_categories(vehicle_scope, sort_order);

-- 3. Universal features dictionary
create table if not exists reverse_search.universal_features (
    id uuid primary key default gen_random_uuid(),
    feature_key text not null unique,
    display_name text not null,
    category_id uuid not null references reverse_search.universal_feature_categories(id) on delete restrict,
    feature_type text not null
        check (feature_type in ('boolean', 'numeric', 'enum', 'text')),
    canonical_unit text null,
    vehicle_scope text not null default 'both'
        check (vehicle_scope in ('passenger', 'commercial', 'both')),
    is_filterable boolean not null default true,
    is_visible_in_card_summary boolean not null default true,
    is_visible_in_brochure boolean not null default true,
    is_service_related boolean not null default false,
    is_bodywork_related boolean not null default false,
    is_required_for_reverse_search boolean not null default false,
    source_standard text not null default 'fleet_excel',
    description text null,
    sort_order integer not null default 100,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_universal_features_category
    on reverse_search.universal_features(category_id, sort_order);

create index if not exists idx_universal_features_scope
    on reverse_search.universal_features(vehicle_scope, is_filterable, is_active);

-- 4. Feature aliases (Excel, catalog, PDF, LLM names)
create table if not exists reverse_search.universal_feature_aliases (
    id uuid primary key default gen_random_uuid(),
    feature_id uuid not null references reverse_search.universal_features(id) on delete cascade,
    alias_text text not null,
    normalized_alias text not null,
    source_type text not null default 'excel_import'
        check (source_type in (
            'excel_import', 'spec', 'variant_doc', 'catalog',
            'brochure', 'price_list', 'manual', 'llm_inference'
        )),
    brand text null,
    language text null default 'pl',
    is_active boolean not null default true,
    created_at timestamptz not null default now()
);

create unique index if not exists idx_universal_feature_aliases_unique
    on reverse_search.universal_feature_aliases(feature_id, normalized_alias, coalesce(brand, ''), coalesce(language, ''));

create index if not exists idx_universal_feature_aliases_normalized
    on reverse_search.universal_feature_aliases(normalized_alias);

create index if not exists idx_universal_feature_aliases_feature
    on reverse_search.universal_feature_aliases(feature_id);

-- 5. Enum values for features
create table if not exists reverse_search.universal_feature_enum_values (
    id uuid primary key default gen_random_uuid(),
    feature_id uuid not null references reverse_search.universal_features(id) on delete cascade,
    enum_key text not null,
    display_name text not null,
    sort_order integer not null default 100,
    is_active boolean not null default true,
    created_at timestamptz not null default now(),
    unique(feature_id, enum_key)
);

create index if not exists idx_universal_feature_enum_values_feature
    on reverse_search.universal_feature_enum_values(feature_id, sort_order);

-- 6. Vehicle context bundles
create table if not exists reverse_search.vehicle_context_bundles (
    id uuid primary key default gen_random_uuid(),
    source_vehicle_id uuid not null,
    bundle_name text not null,
    merge_strategy text not null default 'priority_merge',
    is_active boolean not null default true,
    created_by text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_vehicle_context_bundles_vehicle
    on reverse_search.vehicle_context_bundles(source_vehicle_id, is_active, created_at desc);

-- 7. Bundle documents
create table if not exists reverse_search.vehicle_context_bundle_documents (
    id uuid primary key default gen_random_uuid(),
    bundle_id uuid not null references reverse_search.vehicle_context_bundles(id) on delete cascade,
    document_id uuid null,
    document_role text not null
        check (document_role in (
            'primary_spec', 'variant_doc', 'catalog',
            'brochure', 'price_list', 'fleet_standard'
        )),
    priority_order integer not null default 100,
    selected_by_user boolean not null default true,
    notes text null,
    created_at timestamptz not null default now()
);

create index if not exists idx_vehicle_context_bundle_documents_bundle
    on reverse_search.vehicle_context_bundle_documents(bundle_id, priority_order);

-- 8. Service option catalog
create table if not exists reverse_search.service_option_catalog (
    id uuid primary key default gen_random_uuid(),
    option_key text not null unique,
    display_name text not null,
    option_group text not null default 'bodywork',
    affects_functional_profile boolean not null default true,
    is_active boolean not null default true,
    description text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_service_option_catalog_group
    on reverse_search.service_option_catalog(option_group, is_active);

-- 9. Vehicle service options
create table if not exists reverse_search.vehicle_service_options (
    id uuid primary key default gen_random_uuid(),
    source_vehicle_id uuid not null,
    bundle_id uuid null references reverse_search.vehicle_context_bundles(id) on delete set null,
    service_option_id uuid not null references reverse_search.service_option_catalog(id) on delete restrict,
    status text not null default 'active'
        check (status in ('active', 'inactive', 'draft', 'removed')),
    source_type text not null default 'manual'
        check (source_type in (
            'manual', 'spec', 'catalog', 'brochure',
            'price_list', 'excel_import', 'llm_inference'
        )),
    source_document_id uuid null,
    notes text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists idx_vehicle_service_options_unique
    on reverse_search.vehicle_service_options(source_vehicle_id, service_option_id, coalesce(bundle_id, '00000000-0000-0000-0000-000000000000'::uuid));

create index if not exists idx_vehicle_service_options_vehicle
    on reverse_search.vehicle_service_options(source_vehicle_id, status);

create index if not exists idx_vehicle_service_options_bundle
    on reverse_search.vehicle_service_options(bundle_id);

-- 10. Service option parameters
create table if not exists reverse_search.vehicle_service_option_parameters (
    id uuid primary key default gen_random_uuid(),
    vehicle_service_option_id uuid not null references reverse_search.vehicle_service_options(id) on delete cascade,
    param_key text not null,
    value_num numeric null,
    value_text text null,
    value_bool boolean null,
    unit text null,
    source_type text not null default 'manual'
        check (source_type in (
            'manual', 'spec', 'catalog', 'brochure',
            'price_list', 'excel_import', 'llm_inference'
        )),
    source_document_id uuid null,
    confidence numeric null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(vehicle_service_option_id, param_key)
);

create index if not exists idx_vehicle_service_option_parameters_service_option
    on reverse_search.vehicle_service_option_parameters(vehicle_service_option_id);

-- 11. Vehicle feature evidence (audit trail)
create table if not exists reverse_search.vehicle_feature_evidence (
    id uuid primary key default gen_random_uuid(),
    source_vehicle_id uuid not null,
    bundle_id uuid null references reverse_search.vehicle_context_bundles(id) on delete set null,
    feature_id uuid not null references reverse_search.universal_features(id) on delete cascade,
    document_id uuid null,
    source_type text not null
        check (source_type in (
            'spec', 'variant_doc', 'catalog', 'brochure',
            'price_list', 'excel_import', 'service_option',
            'body_parameters', 'manual_override', 'llm_inference'
        )),
    evidence_status text not null default 'observed'
        check (evidence_status in (
            'observed', 'inferred', 'optional',
            'not_found', 'not_applicable', 'conflict'
        )),
    source_text text null,
    source_path text null,
    value_bool boolean null,
    value_num numeric null,
    value_text text null,
    unit text null,
    confidence numeric null,
    priority_rank integer not null default 100,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_vehicle_feature_evidence_vehicle
    on reverse_search.vehicle_feature_evidence(source_vehicle_id, feature_id);

create index if not exists idx_vehicle_feature_evidence_bundle
    on reverse_search.vehicle_feature_evidence(bundle_id);

create index if not exists idx_vehicle_feature_evidence_source
    on reverse_search.vehicle_feature_evidence(source_type, evidence_status);

-- 12. Vehicle feature state (resolved features — core of reverse discovery)
create table if not exists reverse_search.vehicle_feature_state (
    id uuid primary key default gen_random_uuid(),
    source_vehicle_id uuid not null,
    bundle_id uuid null references reverse_search.vehicle_context_bundles(id) on delete set null,
    feature_id uuid not null references reverse_search.universal_features(id) on delete cascade,
    resolved_status text not null
        check (resolved_status in (
            'present_confirmed_primary',
            'present_confirmed_secondary',
            'present_inferred',
            'optional_package_possible',
            'available_for_configuration',
            'unknown',
            'not_applicable',
            'contradiction_detected'
        )),
    resolved_value_bool boolean null,
    resolved_value_num numeric null,
    resolved_value_text text null,
    resolved_unit text null,
    confidence numeric null,
    resolution_source text null,
    is_manual_override boolean not null default false,
    last_resolved_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists idx_vehicle_feature_state_unique
    on reverse_search.vehicle_feature_state(source_vehicle_id, feature_id, coalesce(bundle_id, '00000000-0000-0000-0000-000000000000'::uuid));

create index if not exists idx_vehicle_feature_state_vehicle
    on reverse_search.vehicle_feature_state(source_vehicle_id);

create index if not exists idx_vehicle_feature_state_feature
    on reverse_search.vehicle_feature_state(feature_id, resolved_status);

create index if not exists idx_vehicle_feature_state_bundle
    on reverse_search.vehicle_feature_state(bundle_id);

create index if not exists idx_vehicle_feature_state_bool
    on reverse_search.vehicle_feature_state(feature_id, resolved_value_bool)
    where resolved_value_bool is not null;

create index if not exists idx_vehicle_feature_state_num
    on reverse_search.vehicle_feature_state(feature_id, resolved_value_num)
    where resolved_value_num is not null;

create index if not exists idx_vehicle_feature_state_text
    on reverse_search.vehicle_feature_state(feature_id, resolved_value_text)
    where resolved_value_text is not null;

-- 13. Vehicle features summary view (reverse discovery flat view)
create or replace view reverse_search.vehicle_features_summary_view as
select
    vfs.source_vehicle_id,
    vfs.bundle_id,
    uf.feature_key,
    uf.display_name,
    ufc.display_name as category_name,
    uf.feature_type,
    vfs.resolved_status,
    vfs.resolved_value_bool,
    vfs.resolved_value_num,
    vfs.resolved_value_text,
    vfs.resolved_unit,
    vfs.confidence,
    vfs.resolution_source,
    uf.is_filterable,
    uf.is_visible_in_card_summary,
    uf.is_visible_in_brochure
from reverse_search.vehicle_feature_state vfs
join reverse_search.universal_features uf on uf.id = vfs.feature_id
join reverse_search.universal_feature_categories ufc on ufc.id = uf.category_id
where uf.is_active = true;

-- 14. Card summary view
create or replace view reverse_search.universal_features_card_summary_view as
select
    source_vehicle_id,
    bundle_id,
    category_name,
    jsonb_agg(
        jsonb_build_object(
            'feature_key', feature_key,
            'display_name', display_name,
            'feature_type', feature_type,
            'resolved_status', resolved_status,
            'value_bool', resolved_value_bool,
            'value_num', resolved_value_num,
            'value_text', resolved_value_text,
            'unit', resolved_unit,
            'confidence', confidence,
            'resolution_source', resolution_source
        )
        order by display_name
    ) as features
from reverse_search.vehicle_features_summary_view
where is_visible_in_card_summary = true
group by source_vehicle_id, bundle_id, category_name;

-- 15. Brochure view
create or replace view reverse_search.universal_features_brochure_view as
select
    source_vehicle_id,
    bundle_id,
    category_name,
    jsonb_agg(
        jsonb_build_object(
            'feature_key', feature_key,
            'display_name', display_name,
            'feature_type', feature_type,
            'resolved_status', resolved_status,
            'value_bool', resolved_value_bool,
            'value_num', resolved_value_num,
            'value_text', resolved_value_text,
            'unit', resolved_unit
        )
        order by display_name
    ) as features
from reverse_search.vehicle_features_summary_view
where is_visible_in_brochure = true
group by source_vehicle_id, bundle_id, category_name;

-- 16. Feature rebuild jobs
create table if not exists reverse_search.feature_rebuild_jobs (
    id uuid primary key default gen_random_uuid(),
    source_vehicle_id uuid not null,
    bundle_id uuid null,
    trigger_type text not null
        check (trigger_type in (
            'excel_import', 'document_import', 'service_option_change',
            'body_parameter_change', 'manual_override',
            'bundle_change', 'full_rebuild'
        )),
    status text not null default 'queued'
        check (status in ('queued', 'running', 'completed', 'failed')),
    error_message text null,
    created_at timestamptz not null default now(),
    started_at timestamptz null,
    finished_at timestamptz null
);

create index if not exists idx_feature_rebuild_jobs_status
    on reverse_search.feature_rebuild_jobs(status, created_at);

-- 17. Import run tracking
create table if not exists reverse_search.feature_import_runs (
    id uuid primary key default gen_random_uuid(),
    import_type text not null
        check (import_type in ('excel_standard', 'excel_vehicle_mapping')),
    file_name text not null,
    source_path text null,
    imported_by text null,
    import_summary jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now()
);

-- 18. Trigger function for updated_at
create or replace function reverse_search.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

-- Apply updated_at triggers to all mutable tables
drop trigger if exists trg_universal_feature_categories_updated_at on reverse_search.universal_feature_categories;
create trigger trg_universal_feature_categories_updated_at
before update on reverse_search.universal_feature_categories
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_universal_features_updated_at on reverse_search.universal_features;
create trigger trg_universal_features_updated_at
before update on reverse_search.universal_features
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_service_option_catalog_updated_at on reverse_search.service_option_catalog;
create trigger trg_service_option_catalog_updated_at
before update on reverse_search.service_option_catalog
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_vehicle_context_bundles_updated_at on reverse_search.vehicle_context_bundles;
create trigger trg_vehicle_context_bundles_updated_at
before update on reverse_search.vehicle_context_bundles
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_vehicle_service_options_updated_at on reverse_search.vehicle_service_options;
create trigger trg_vehicle_service_options_updated_at
before update on reverse_search.vehicle_service_options
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_vehicle_service_option_parameters_updated_at on reverse_search.vehicle_service_option_parameters;
create trigger trg_vehicle_service_option_parameters_updated_at
before update on reverse_search.vehicle_service_option_parameters
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_vehicle_feature_evidence_updated_at on reverse_search.vehicle_feature_evidence;
create trigger trg_vehicle_feature_evidence_updated_at
before update on reverse_search.vehicle_feature_evidence
for each row execute function reverse_search.set_updated_at();

drop trigger if exists trg_vehicle_feature_state_updated_at on reverse_search.vehicle_feature_state;
create trigger trg_vehicle_feature_state_updated_at
before update on reverse_search.vehicle_feature_state
for each row execute function reverse_search.set_updated_at();

-- 19. Seed base categories
insert into reverse_search.universal_feature_categories (category_key, display_name, vehicle_scope, sort_order)
values
    ('dimensions', 'Wymiary', 'both', 10),
    ('cargo', 'Cargo / Ładunek', 'commercial', 20),
    ('loading', 'Załadunek', 'commercial', 25),
    ('bodywork', 'Zabudowa', 'commercial', 30),
    ('towing', 'Holowanie / Hak', 'both', 35),
    ('lpg', 'Instalacja LPG', 'both', 40),
    ('refrigeration', 'Chłodnia / Izoterma', 'commercial', 45),
    ('lift_tachograph', 'Winda / Tachograf / Wywrot', 'commercial', 50),
    ('drivetrain', 'Napęd / Paliwo / EV', 'both', 55),
    ('body_type', 'Typ zabudowy', 'commercial', 58),
    ('comfort', 'Komfort', 'both', 60),
    ('safety', 'Bezpieczeństwo', 'both', 70),
    ('multimedia', 'Multimedia', 'both', 80),
    ('seats', 'Fotele', 'both', 85),
    ('lighting', 'Oświetlenie', 'both', 88),
    ('security', 'Zabezpieczenia', 'both', 90),
    ('cabin', 'Kabina / Dach', 'commercial', 92),
    ('energy', 'Energia i napęd', 'both', 95)
on conflict (category_key) do nothing;

-- 20. Grants for API access
grant usage on schema reverse_search to anon, authenticated;
grant all on all tables in schema reverse_search to anon, authenticated;
grant all on all sequences in schema reverse_search to anon, authenticated;
alter default privileges in schema reverse_search grant all on tables to anon, authenticated;
alter default privileges in schema reverse_search grant all on sequences to anon, authenticated;
