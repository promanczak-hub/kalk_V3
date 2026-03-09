-- Migration: Create Catalog Library tables for multi-document feature mapping
-- Tables:
--   1. model_document_sources — versioned catalogs and price lists
--   2. vehicle_catalog_matches — audit: which catalog matched which vehicle
-- Storage:
--   Supabase bucket: catalog-documents

BEGIN;

-- ================================================
-- 1. Table: model_document_sources
-- ================================================
CREATE TABLE IF NOT EXISTS reverse_search.model_document_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identification (brand + model family scope)
    brand TEXT NOT NULL,
    model_family TEXT NOT NULL,
    document_type TEXT NOT NULL
        CHECK (document_type IN ('catalog', 'price_list')),

    -- Versioning (user-defined label)
    display_name TEXT NOT NULL,
    version_tag TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Source file
    file_type TEXT NOT NULL
        CHECK (file_type IN ('pdf', 'xlsx', 'csv')),
    storage_path TEXT NOT NULL,
    original_filename TEXT,
    file_size_bytes BIGINT,

    -- Extracted data (JSON with variants and features)
    extracted_data JSONB,
    extraction_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (extraction_status IN (
            'pending', 'extracting', 'ready', 'error'
        )),
    extraction_error TEXT,
    variant_count INT NOT NULL DEFAULT 0,

    -- Audit
    uploaded_by TEXT,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extracted_at TIMESTAMPTZ,

    -- Unique: same brand+model can have multiple versions with different names
    UNIQUE(brand, model_family, document_type, display_name)
);

-- Index for fast lookup by brand+model
CREATE INDEX IF NOT EXISTS idx_mds_brand_model
ON reverse_search.model_document_sources(brand, model_family);

-- Index for active documents
CREATE INDEX IF NOT EXISTS idx_mds_active
ON reverse_search.model_document_sources(brand, model_family, is_active)
WHERE is_active = TRUE;

COMMENT ON TABLE reverse_search.model_document_sources IS
    'Global document sources (catalogs, price lists) per brand/model family with versioning';


-- ================================================
-- 2. Table: vehicle_catalog_matches (audit trail)
-- ================================================
CREATE TABLE IF NOT EXISTS reverse_search.vehicle_catalog_matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Links
    source_vehicle_id UUID NOT NULL,
    catalog_source_id UUID NOT NULL
        REFERENCES reverse_search.model_document_sources(id)
        ON DELETE CASCADE,

    -- Match result
    matched_variant_name TEXT,
    match_confidence NUMERIC(3,2),
    features_extracted INT NOT NULL DEFAULT 0,

    -- Audit
    matched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    matched_by TEXT,

    -- One match per vehicle+catalog pair
    UNIQUE(source_vehicle_id, catalog_source_id)
);

CREATE INDEX IF NOT EXISTS idx_vcm_vehicle
ON reverse_search.vehicle_catalog_matches(source_vehicle_id);

COMMENT ON TABLE reverse_search.vehicle_catalog_matches IS
    'Audit trail: which catalog was cross-referenced with which vehicle';


-- ================================================
-- 3. RLS policies
-- ================================================

-- model_document_sources
ALTER TABLE reverse_search.model_document_sources ENABLE ROW LEVEL SECURITY;

CREATE POLICY "model_document_sources_select"
ON reverse_search.model_document_sources FOR SELECT
USING (TRUE);

CREATE POLICY "model_document_sources_insert"
ON reverse_search.model_document_sources FOR INSERT
WITH CHECK (TRUE);

CREATE POLICY "model_document_sources_update"
ON reverse_search.model_document_sources FOR UPDATE
USING (TRUE);

CREATE POLICY "model_document_sources_delete"
ON reverse_search.model_document_sources FOR DELETE
USING (TRUE);


-- vehicle_catalog_matches
ALTER TABLE reverse_search.vehicle_catalog_matches ENABLE ROW LEVEL SECURITY;

CREATE POLICY "vehicle_catalog_matches_select"
ON reverse_search.vehicle_catalog_matches FOR SELECT
USING (TRUE);

CREATE POLICY "vehicle_catalog_matches_insert"
ON reverse_search.vehicle_catalog_matches FOR INSERT
WITH CHECK (TRUE);

CREATE POLICY "vehicle_catalog_matches_update"
ON reverse_search.vehicle_catalog_matches FOR UPDATE
USING (TRUE);

CREATE POLICY "vehicle_catalog_matches_delete"
ON reverse_search.vehicle_catalog_matches FOR DELETE
USING (TRUE);

COMMIT;
