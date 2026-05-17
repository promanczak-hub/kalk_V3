-- Drop 18 legacy/orphan tables po audycie referencji w produkcji.
-- transport_fees zachowana per decyzja uzytkownika (feature placeholder, ma fallback w kodzie).
-- powertrain_types NIE droppujemy — uzywana przez fn_powertrain_family (SOT GSheet _dict_powertrains).

-- Nieuzywana kolumna FK (do droppowanej vehicle_categories)
ALTER TABLE public.body_types DROP COLUMN IF EXISTS vehicle_category_id;

-- Tier 1: Legacy WR system (zastapiony przez samar_class_*_rv / body_types.utrata_wartosci / paint_types)
DROP TABLE IF EXISTS public._archive_body_type_wr_corrections;
DROP TABLE IF EXISTS public.nadwozie_wr_corrections;
DROP TABLE IF EXISTS public.ltr_admin_tabela_wr_deprecjacjas;
DROP TABLE IF EXISTS public.ltr_admin_tabela_wr_klasas;
DROP TABLE IF EXISTS public.ltr_admin_tabela_wr_przebiegs;
DROP TABLE IF EXISTS public.ltr_admin_korekta_wr_kolors;
DROP TABLE IF EXISTS public.equipment_wr_corrections;

-- Tier 2: empty + zero referencji w prod
DROP TABLE IF EXISTS public.saved_search_matches;
DROP TABLE IF EXISTS public.saved_searches;
DROP TABLE IF EXISTS public.service_base_costs_config;

-- Tier 3: orphan lookups + nieuzywane drafts (calculator_excel_data: route + table razem)
DROP TABLE IF EXISTS public.excel_drafts;
DROP TABLE IF EXISTS public.document_library;
DROP TABLE IF EXISTS public.config_table_versions;
DROP TABLE IF EXISTS public.brands_dict;
DROP TABLE IF EXISTS public.drivetrain_types;
DROP TABLE IF EXISTS public.vehicle_categories;
DROP TABLE IF EXISTS public.calculator_excel_data;
