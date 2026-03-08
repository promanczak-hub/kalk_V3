"""Check KlasaSAMAR_czak class names vs samar_classes names - write to file."""

from core.database import supabase

rows = supabase.table("KlasaSAMAR_czak").select("col_1").execute()
czak_names = sorted(set(str(r["col_1"]).strip() for r in rows.data if r.get("col_1")))

sc_rows = supabase.table("samar_classes").select("id, name").order("id").execute()
sc_names = [(r["id"], r["name"].strip()) for r in sc_rows.data]

with open("tmp_output.txt", "w", encoding="utf-8") as f:
    f.write("CZAK NAMES:\n")
    for n in czak_names:
        f.write(f"  {n}\n")
    f.write(f"\nsamar_classes NAMES:\n")
    for sid, n in sc_names:
        f.write(f"  id={sid:3d}: {n}\n")
    has_klasa = any("Klasa" in n or "klasa" in n for n in czak_names)
    f.write(f"\nCzak has 'Klasa' in names: {has_klasa}\n")

print("Written to tmp_output.txt")
