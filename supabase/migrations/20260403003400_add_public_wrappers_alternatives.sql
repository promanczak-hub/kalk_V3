-- Public wrappers for alternatives RPCs (PostgREST requires functions in 'public' schema)

CREATE OR REPLACE FUNCTION public.rpc_get_alternatives_math(
    p_vehicle_id uuid,
    p_category text,
    p_limit integer DEFAULT 5,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer
)
 RETURNS TABLE(similarity_json jsonb)
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $$
    SELECT * FROM reverse_search.rpc_get_alternatives_math(
        p_vehicle_id, p_category, p_limit, p_duration_months, p_annual_mileage
    );
$$;

CREATE OR REPLACE FUNCTION public.rpc_get_alternatives_semantic(
    p_vehicle_id uuid,
    p_synthetic_vector vector(768),
    p_limit integer DEFAULT 5,
    p_duration_months integer DEFAULT NULL::integer,
    p_annual_mileage integer DEFAULT NULL::integer
)
 RETURNS TABLE(similarity_json jsonb)
 LANGUAGE sql
 STABLE SECURITY DEFINER
AS $$
    SELECT * FROM reverse_search.rpc_get_alternatives_semantic(
        p_vehicle_id, p_synthetic_vector, p_limit, p_duration_months, p_annual_mileage
    );
$$;
