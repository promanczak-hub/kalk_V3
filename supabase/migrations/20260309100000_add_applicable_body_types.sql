-- Add applicable_body_types to universal_features

ALTER TABLE reverse_search.universal_features
ADD COLUMN applicable_body_types text[] DEFAULT NULL;

COMMENT ON COLUMN reverse_search.universal_features.applicable_body_types IS 'List of body types (e.g., Furgon, Chłodnia) this feature applies to. null means applicable to all.';
