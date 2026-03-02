from dotenv import load_dotenv

load_dotenv(".env")
from core.database import supabase

try:
    res = supabase.table("koszty_serwisowe").select("*").limit(5).execute()
    if res.data:
        print("Columns in koszty_serwisowe: ", res.data[0].keys())
        print(res.data[0])
except Exception as e:
    print("error koszty_serwisowe", e)

try:
    res2 = supabase.table("engines").select("*").limit(5).execute()
    if res2.data:
        print("Columns in engines: ", res2.data[0].keys())
        print(res2.data[0])
except Exception as e:
    print("error engines", e)

try:
    res3 = supabase.table("tabele_rms_czak").select("*").limit(5).execute()
    if res3.data:
        print("Columns in tabele_rms_czak: ", res3.data[0].keys())
        print(res3.data[0])
except Exception as e:
    print("error tabele_rms_czak", e)
