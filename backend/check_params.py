from core.database import supabase

res = supabase.table("LTRAdminParametry_czak").select("col_1, col_2").execute()
for i in res.data:
    if i.get("col_1") in [
        "ZarejestrowanieKartaPojazdu",
        "HakHolowniczy",
        "AbonamentGSM",
        "CenaUrzadzeniaGSM",
        "MontazUrzadzeniaGSM",
        "PrzygotowanieDoSprzedazyRacMtr",
        "PrzygotowanieDoSprzedazyLtr",
        "KosztWymontowaniaKraty",
    ]:
        print(f"{i.get('col_1')}: {i.get('col_2')}")

try:
    gsm = supabase.table("LTRAdminGSM_czak").select("*").limit(5).execute()
    print("LTRAdminGSM_czak count:", len(gsm.data))
    if gsm.data:
        print("Sample:", gsm.data[0])
except Exception as e:
    print("Error getting GSM table:", e)
