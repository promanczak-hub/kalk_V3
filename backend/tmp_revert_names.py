"""
Revert samar_classes names back to original format (without 'Klasa').
The 'Klasa' prefix creates format mismatch with:
  - KlasaSAMAR_czak (source of AI classification)
  - existing vehicle_synthesis data
  - frozen samar_rv.py cache
"""

from core.database import supabase

# Original names (without 'Klasa' prefix) - matching KlasaSAMAR_czak
ORIGINAL_NAMES: dict[int, str] = {
    1: "PODSTAWOWA A MINI",
    2: "PODSTAWOWA B MAŁE",
    3: "PODSTAWOWA C NIŻSZA ŚREDNIA",
    4: "PODSTAWOWA D ŚREDNIA",
    5: "PODSTAWOWA E WYŻSZA",
    6: "PODSTAWOWA F LUKSUSOWE, G S. LUKSUSOWE",
    12: "SPORTOWO-REKREACYJNE A MINI",
    13: "SPORTOWO-REKREACYJNE B MAŁE",
    14: "TERENOWO-REKREACYJNE B MAŁE",
    15: "VANY B MICROVANY",
    16: "SPORTOWO-REKREACYJNE C NIŻSZA ŚREDNIA",
    17: "TERENOWO-REKREACYJNE C NIŻSZA ŚREDNIA",
    18: "VANY C MINIVANY",
    19: "SPORTOWO-REKREACYJNE D ŚREDNIA",
    20: "TERENOWO-REKREACYJNE D ŚREDNIA",
    21: "VANY D VANY",
    22: "TERENOWO-REKREACYJNE E WYŻSZA",
    23: "SPORTOWO-REKREACYJNE F LUKSUSOWE, G S. LUKSUSOWE",
    24: "TERENOWO-REKREACYJNE G S. LUKSUSOWE",
    25: "KOMBIVANY H KOMBI-VANY",
    26: "S. DOSTAWCZE I CIĘŻAROWE DO 6T KOMBI VAN, VAN",
    27: "MINIBUS I MINIBUS",
    28: "S. DOSTAWCZE I CIĘŻAROWE DO 6T ŚREDNIE DOSTAWCZE, CIĘŻKIE DOSTAWCZE, AUTOBUSY",
    29: "S. DOSTAWCZE I CIĘŻAROWE DO 6T PICK-UP",
}

updated = 0
for sid, name in ORIGINAL_NAMES.items():
    res = supabase.table("samar_classes").update({"name": name}).eq("id", sid).execute()
    if res.data:
        updated += 1

with open("tmp_revert_out.txt", "w", encoding="utf-8") as f:
    f.write(f"Reverted {updated} names back to original format\n")

    # Verify
    sc = supabase.table("samar_classes").select("id, name").order("id").execute()
    f.write(f"\nVerification ({len(sc.data)} entries):\n")
    for r in sc.data:
        f.write(f"  id={r['id']:3d}: {r['name']}\n")

print(f"Done. Reverted {updated} names. See tmp_revert_out.txt")
