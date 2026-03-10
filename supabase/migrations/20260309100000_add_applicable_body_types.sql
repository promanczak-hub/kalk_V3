-- Add applicable_body_types to universal_features

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'reverse_search'
          AND table_name = 'universal_features'
          AND column_name = 'applicable_body_types'
    ) THEN
        ALTER TABLE reverse_search.universal_features ADD COLUMN applicable_body_types text[] DEFAULT NULL;
    END IF;
END
$$;

COMMENT ON COLUMN reverse_search.universal_features.applicable_body_types IS 'List of body types (e.g., Furgon, Chłodnia) this feature applies to. null means applicable to all.';
