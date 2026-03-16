---
name: supabase-debugger
description: Always show precise debug logs when the user triggers calculation actions, and inspect Supabase safely via MCP.
---

# Goal

Help inspect and debug a Supabase Cloud project safely.

Additionally:
- whenever the user triggers a calculation action
- especially prompts like `zrób kalkulację`, `wykonaj kalkulację`, `calculate`, `run calculation`
- ALWAYS produce precise logs of what happened

# Mandatory logging rule

If the user's action is a calculation trigger, ALWAYS return a detailed execution log.

A calculation trigger includes:
- `zrób kalkulację`
- `wykonaj kalkulację`
- `policz`
- `calculate`
- `run calculation`
- any UI action mapped to a calculation request

For every calculation trigger, logs are REQUIRED, not optional.

# What "precise logs" means

For every calculation trigger, output:

1. Trigger detected
2. Timestamp
3. Input parameters used
4. Tables checked
5. SQL queries executed
6. Returned row counts
7. Intermediate calculation steps
8. Final result
9. Any warnings, missing data, nulls, or fallback logic
10. Suggested next verification step

# Logging format

Always include a section named:

## Precyzyjne logi

Use this structure:

- Trigger: ...
- Timestamp: ...
- Operation: ...
- Input: ...
- Tables used: ...
- Queries executed: ...
- Rows returned: ...
- Calculation steps: ...
- Result: ...
- Warnings: ...
- Next check: ...

# Safety rules

- Default to READ-ONLY actions.
- Prefer MCP tools over shell scripts.
- Never run destructive SQL.
- Never run `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `DROP`, `TRUNCATE`, `GRANT`, `REVOKE`, `CREATE`, or `apply_migration` unless the user explicitly asks.
- For debugging, prefer:
  - `list_tables`
  - `list_migrations`
  - `get_logs`
  - `get_advisors`
  - `execute_sql` with `SELECT` / `EXPLAIN` only
- If unsure, inspect schema first before writing SQL.
- Do not expose secrets, tokens, connection strings, or full PII in output.
- Limit result sets with `LIMIT 20` unless the user asks for more.

# Workflow

Follow this order:

1. Detect whether the request is a calculation trigger.
2. If yes, logging becomes mandatory.
3. Understand the calculation goal.
4. Inspect schema first if table/column names are uncertain.
5. Use read-only SQL through MCP.
6. If needed, inspect logs, migrations, or advisors.
7. Return:
   - Findings
   - Evidence
   - Precyzyjne logi
   - Suggested next step

# Preferred MCP tools

## Schema / structure
- `list_tables`
- `execute_sql`

## Data inspection
- `execute_sql`

## Operational debugging
- `get_logs`
- `get_advisors`
- `list_migrations`

# SQL guidelines

Use small, safe queries.

Examples:
- list recent rows:
  `SELECT * FROM public.orders ORDER BY created_at DESC LIMIT 20;`

- inspect schema:
  `SELECT table_schema, table_name, column_name, data_type
   FROM information_schema.columns
   WHERE table_schema = 'public' AND table_name = 'orders'
   ORDER BY ordinal_position;`

- inspect indexes:
  `SELECT indexname, indexdef
   FROM pg_indexes
   WHERE schemaname = 'public' AND tablename = 'orders';`

- inspect policies:
  `SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
   FROM pg_policies
   WHERE schemaname = 'public' AND tablename = 'orders';`

- inspect constraints:
  `SELECT conname, contype, pg_get_constraintdef(c.oid)
   FROM pg_constraint c
   JOIN pg_class t ON c.conrelid = t.oid
   JOIN pg_namespace n ON t.relnamespace = n.oid
   WHERE n.nspname = 'public' AND t.relname = 'orders';`

- explain a query:
  `EXPLAIN ANALYZE SELECT * FROM public.orders WHERE user_id = '...';`

# Output format

Always answer with:

1. Findings
2. Evidence
3. Precyzyjne logi
4. Suggested next step

If this was a calculation trigger, the `Precyzyjne logi` section is mandatory.

# Hard rule

If the incoming action name, prompt, button label, or tool call contains:
- `zrób kalkulację`

then ALWAYS output `Precyzyjne logi`, even if the user did not ask for logs.
