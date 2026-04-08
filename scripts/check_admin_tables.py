import sys

sys.path.append(r"d:\kalk_v3\backend")
from core.database import supabase

# Fetch dicts from DB to see what the pipeline expects
res_przebieg = (
    supabase.table("ltr_admin_tabela_wr_przebiegs").select("*").limit(10).execute()
)
print("ltr_admin_tabela_wr_przebiegs sample:")
for r in res_przebieg.data:
    print(r)

res_klasa = supabase.table("ltr_admin_tabela_wr_klasas").select("*").limit(10).execute()
print("\nltr_admin_tabela_wr_klasas sample:")
for r in res_klasa.data:
    print(r)

res_samar = supabase.table("samar_classes").select("*").limit(5).execute()
print("\nsamar_classes sample:")
for r in res_samar.data:
    print(r)
