"""List all Supabase tables and their columns."""

import os

os.environ.setdefault("GEMINI_API_KEY", "dummy")
from core.database import supabase

# Check what tables exist by trying common ones
tables_to_check = [
    "ltr_kalkulacje",
    "control_center",
    "pojazdy_master",
    "pojazdy",
    "samar_klasa_wr",
    "ltr_admin_ubezpieczenia",
    "ltr_admin_stawka_zastepczy",
    "ltr_admin_wspolczynniki_szkodowe",
    "ltr_admin_tabela_wr_deprecjacjas",
    "ltr_admin_opony",
]

for t in tables_to_check:
    try:
        res = supabase.table(t).select("*").limit(1).execute()
        cols = list(res.data[0].keys()) if res.data else ["(empty)"]
        print(f"OK  {t}: {len(res.data)} rows, cols={cols}")
    except Exception as e:
        err = str(e)[:80]
        print(f"ERR {t}: {err}")
