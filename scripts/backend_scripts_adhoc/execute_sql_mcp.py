import json

with open("d:/kalk_v3/backend/sql_chunks.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

# The sql_chunks.json holds individual INSERT statements or CREATE TABLE statements.
print("Total commands to execute:", len(chunks))

# I will write the commands back in groups of 5 so that I can use MCP on them.
mcp_scripts = []
for i in range(0, len(chunks), 5):
    batch = "\n".join(chunks[i : i + 5])
    mcp_scripts.append(batch)

with open("d:/kalk_v3/backend/mcp_execute_group.json", "w", encoding="utf-8") as f:
    json.dump(mcp_scripts, f)

print(f"Divided into {len(mcp_scripts)} MCP payload batches.")
