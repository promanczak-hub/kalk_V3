
with open("d:/kalk_v3/deploy_to_cloud.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Split statements safely
statements = []
current = []
in_quote = False
for char in sql:
    if char == "'":
        in_quote = not in_quote
    current.append(char)
    if char == ";" and not in_quote:
        stmt = "".join(current).strip()
        if stmt:
            statements.append(stmt)
        current = []

if "".join(current).strip():
    statements.append("".join(current).strip())

batches = []
for i in range(0, len(statements), 15):
    batch = "\n".join(statements[i : i + 15])
    batches.append(batch)

for i, batch in enumerate(batches[:20]):  # Write 20 batches to file
    with open(f"d:/kalk_v3/backend/sql_batch_{i}.txt", "w", encoding="utf-8") as f:
        f.write(batch)

print(f"Created {len(batches)} batches in total.")
