-- Add metadata jsonb to universal_features to support enum options and other flexible properties
ALTER TABLE reverse_search.universal_features ADD COLUMN IF NOT EXISTS metadata jsonb;
