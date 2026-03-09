-- Migration: Add unique constraint for evidence upsert
-- Required for ON CONFLICT(source_vehicle_id, feature_id, source_type)
-- used by feature_enrichment.py and feature_cross_reference.py

CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicle_feature_evidence_upsert
    ON reverse_search.vehicle_feature_evidence(
        source_vehicle_id, feature_id, source_type
    );
