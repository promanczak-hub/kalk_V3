-- Config Table Versioning
-- Tracks snapshots of configuration tables for rollback and audit

CREATE TABLE IF NOT EXISTS config_table_versions (
    id          BIGSERIAL PRIMARY KEY,
    table_name  TEXT NOT NULL,
    version_num INTEGER NOT NULL,
    label       TEXT DEFAULT '',
    snapshot    JSONB NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    created_by  TEXT DEFAULT 'system'
);

CREATE INDEX IF NOT EXISTS idx_ctv_table
    ON config_table_versions(table_name, version_num DESC);

-- RLS: allow all for anon (local dev)
ALTER TABLE config_table_versions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow all for anon" ON config_table_versions
    FOR ALL USING (true) WITH CHECK (true);
