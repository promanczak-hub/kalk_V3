"""Check SAMAR classes and KlasaSAMAR_czak dictionary."""

import os

os.environ.setdefault("VITE_SUPABASE_URL", "http://127.0.0.1:54321")
os.environ.setdefault(
    "VITE_SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9."
    "CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0",
)

from supabase import create_client

sb = create_client(
    os.environ["VITE_SUPABASE_URL"],
    os.environ["VITE_SUPABASE_ANON_KEY"],
)

print("=" * 60)
print("1. samar_classes table:")
print("=" * 60)
sc = sb.table("samar_classes").select("id, name").order("id").execute()
for r in sc.data:
    print(f"  {r['id']:3} | {r['name']}")
print(f"\n  TOTAL: {len(sc.data)} classes\n")

print("=" * 60)
print("2. KlasaSAMAR_czak dictionary table:")
print("=" * 60)
try:
    kd = (
        sb.table("KlasaSAMAR_czak")
        .select("col_1, col_8, col_9")
        .order("col_9")
        .execute()
    )
    unique_classes = set()
    for r in kd.data:
        klasa = (r.get("col_1") or "").strip()
        if klasa:
            unique_classes.add(klasa)
    for cls in sorted(unique_classes):
        print(f"  - {cls}")
    print(f"\n  TOTAL rows: {len(kd.data)}, unique classes: {len(unique_classes)}")
except Exception as e:
    print(f"  ERROR: {e}")

print()
print("=" * 60)
print("3. Mapping check - classes in KlasaSAMAR_czak vs samar_classes:")
print("=" * 60)
sc_names = {r["name"] for r in sc.data}
if "unique_classes" in dir():
    in_dict_not_sc = unique_classes - sc_names
    in_sc_not_dict = sc_names - unique_classes
    if in_dict_not_sc:
        print("  Classes in KlasaSAMAR_czak but NOT in samar_classes:")
        for c in sorted(in_dict_not_sc):
            print(f"    - {c}")
    if in_sc_not_dict:
        print("  Classes in samar_classes but NOT in KlasaSAMAR_czak:")
        for c in sorted(in_sc_not_dict):
            print(f"    - {c}")
    if not in_dict_not_sc and not in_sc_not_dict:
        print("  PERFECT MATCH!")
