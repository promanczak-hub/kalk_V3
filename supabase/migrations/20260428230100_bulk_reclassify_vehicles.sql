-- One-time cleanup: re-run classification for every vehicle now that
-- rpc_sync_classification_features filters out non-filterable features.
-- Removes the 13 deprecated naked variants (and any other non-filterable noise)
-- from vehicle_synthesis.feature_keys_present.

DO $$
DECLARE
    v_id uuid;
    v_count int := 0;
BEGIN
    FOR v_id IN SELECT id FROM public.vehicle_synthesis LOOP
        PERFORM reverse_search.rpc_sync_classification_features(v_id);
        v_count := v_count + 1;
    END LOOP;
    RAISE NOTICE 'Reclassified % vehicles', v_count;
END $$;
