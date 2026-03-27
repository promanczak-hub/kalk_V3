-- Description: Drop obsolete signatures of rpc_get_available_filters that lack the p_body_types parameter.
-- This resolves the PGRST203 (Multiple Choices) error caused by PostgreSQL being unable to resolve function overloads correctly when defaults are used.

DROP FUNCTION IF EXISTS public.rpc_get_available_filters(text[], text[], integer[], jsonb);
DROP FUNCTION IF EXISTS reverse_search.rpc_get_available_filters(text[], text[], integer[], jsonb);
