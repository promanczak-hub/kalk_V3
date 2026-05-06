-- service_role nie miał USAGE/SELECT na schema reverse_search, więc backendowe
-- wywołania scoring_search RPC pod service_role (timeout 2min, ucieczka od
-- anon's 3s) padały na "permission denied for schema reverse_search" już
-- przy planowaniu RETURN QUERY w rpc_get_similar_vehicles_batch_semantic.
-- Anon ma te grants od dawna; tu po prostu wyrównujemy service_role do anon.

GRANT USAGE ON SCHEMA reverse_search TO service_role;

GRANT SELECT ON ALL TABLES IN SCHEMA reverse_search TO service_role;

ALTER DEFAULT PRIVILEGES IN SCHEMA reverse_search
  GRANT SELECT ON TABLES TO service_role;
