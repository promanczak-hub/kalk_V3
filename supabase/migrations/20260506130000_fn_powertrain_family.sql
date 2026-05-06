-- A4a: Helper that maps raw mapped_ai_data.fuel value (e.g. "Benzyna (PB)")
-- to its powertrain family code (ice / mhev / hev / phev / bev / fcev / lpg).
-- Direct lookup against public.powertrain_types.name_pl — verified 1:1 match
-- against current vehicle_synthesis data (7 distinct fuel values, all match).
--
-- Used by rpc_get_similar_vehicles_*_semantic to compute fuel_match at family
-- level instead of strict string equality. This means 1.5 TSI vs 2.0 TSI = match
-- (both ICE), but TSI vs mHEV = mismatch (different families per SOT).

CREATE OR REPLACE FUNCTION public.fn_powertrain_family(fuel_text text)
RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT family FROM public.powertrain_types WHERE name_pl = fuel_text LIMIT 1;
$$;

COMMENT ON FUNCTION public.fn_powertrain_family(text) IS
'Maps raw fuel label (mapped_ai_data.fuel) to powertrain family code via powertrain_types lookup.';
