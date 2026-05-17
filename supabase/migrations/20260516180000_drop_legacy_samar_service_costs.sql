-- Drop legacy table samar_service_costs.
-- Superseded by samar_class_service_rates (introduced in 20260327000000_gsheets_schema_rebuild.sql).
-- Verified empty (0 rows) and no dependents (views/matviews/functions/external FKs)
-- before drop on 2026-05-16.

DROP TABLE IF EXISTS public.samar_service_costs;
