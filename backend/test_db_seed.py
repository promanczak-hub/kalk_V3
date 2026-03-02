import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv("../frontend/.env.local")
supabase = create_client(
    os.getenv("VITE_SUPABASE_URL"), "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
)


def check(table, select_cols):
    try:
        r = supabase.table(table).select(select_cols).limit(1).execute()
        r2 = supabase.table(table).select("id", count="exact").execute()
        count = r2.count if hasattr(r2, "count") else len(r2.data)

        print(
            f"✅ {table}: {count} rekordow | Próbka: {r.data[0] if r.data else 'Brak'}"
        )
    except Exception as e:
        print(f"❌ {table}: Blad - {str(e)}")


print("Sprawdzam baze Supabase...")
check("control_center", "id, cost_sales_prep, cost_registration")
check("tyre_configurations", "config_key, config_value")
check("replacement_car_rates", "samar_class_id, daily_rate_net")
