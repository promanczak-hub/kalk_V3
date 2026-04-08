import sys

sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase

res_klasa = supabase.table("ltr_admin_tabela_wr_klasas").select("klasa").execute()
klasas = [r["klasa"] for r in res_klasa.data]
print(f"ltr_admin_tabela_wr_klasas has {len(klasas)} rows. Sample keys (klasa):")
print(klasas[:20])

res_przebieg = supabase.table("ltr_admin_tabela_wr_przebiegs").select("klasa").execute()
przebiegs = [r["klasa"] for r in res_przebieg.data]
print(
    f"\nltr_admin_tabela_wr_przebiegs has {len(przebiegs)} rows. Sample keys (klasa):"
)
print(przebiegs[:20])

res_okres = supabase.table("ltr_admin_tabela_wr_deprecjacjas").select("klasa").execute()
if res_okres.data:
    okres = [r["klasa"] for r in res_okres.data]
    print(f"\nltr_admin_tabela_wr_deprecjacjas has {len(okres)} rows. Unique keys:")
    print(list(set(okres))[:20])
