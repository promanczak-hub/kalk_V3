from core.database import supabase

result = (
    supabase.table("samar_classes")
    .select("id, name, description")
    .order("id")
    .execute()
)

with open("tmp_classes_output.txt", "w", encoding="utf-8") as f:
    f.write(f"Total: {len(result.data)} klas\n\n")
    for r in result.data:
        f.write(f"ID {r['id']:3d} | {r['name']}\n")

print("Done - see tmp_classes_output.txt")
