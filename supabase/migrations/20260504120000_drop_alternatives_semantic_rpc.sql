-- Drop rpc_get_alternatives_semantic — endpoint /alternatives-blend was removed
-- in favor of a single similarity tier (rpc_get_similar_vehicles_batch_semantic).

DROP FUNCTION IF EXISTS public.rpc_get_alternatives_semantic(uuid, vector, integer, integer, integer, jsonb);
DROP FUNCTION IF EXISTS reverse_search.rpc_get_alternatives_semantic(uuid, vector, integer, integer, integer, jsonb);
