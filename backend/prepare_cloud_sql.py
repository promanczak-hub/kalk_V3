import urllib.request
import json
import urllib.error

# Project: gnpsdiarmwvqhqbyetce
# I'll use the MCP Supabase execute_sql tool for this since it has proper auth.
# Wait, this script generates the combined SQL string which I will pass to MCP or run via local python if I have the password.
# Since I do not know the postgres password for the cloud DB, I MUST use MCP execute_sql if possible.
# But MCP execute_sql requires project_id and query. Let's output the merged query to a file.

with open('d:/kalk_v3/supabase/migrations/20260308170000_create_reverse_search_schema.sql', 'r', encoding='utf-8') as f:
    sql1 = f.read()

with open('d:/kalk_v3/supabase/migrations/20260310120000_add_metadata_to_universal_features.sql', 'r', encoding='utf-8') as f:
    sql2 = f.read()

with open('d:/kalk_v3/seed_features.sql', 'r', encoding='utf-8') as f:
    sql3 = f.read()

sql4 = """
-- Add access to the API
GRANT USAGE ON SCHEMA reverse_search TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA reverse_search TO anon, authenticated;
-- Important: For Supabase Cloud, the PostgREST schema exposure is managed in the Dashboard API settings.
-- We can also try altering the authenticator role:
ALTER ROLE authenticator SET pgrst.db_schemas TO 'public, graphql_public, reverse_search';
NOTIFY pgrst, 'reload config';
"""

merged = sql1 + "\n\n" + sql2 + "\n\n" + sql3 + "\n\n" + sql4

with open('d:/kalk_v3/deploy_to_cloud.sql', 'w', encoding='utf-8') as f:
    f.write(merged)

print("Created deploy_to_cloud.sql")
