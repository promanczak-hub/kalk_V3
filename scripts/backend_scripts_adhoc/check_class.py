import asyncio
import os
from dotenv import load_dotenv
import json

load_dotenv()
load_dotenv("../frontend/.env.local")

from core.database import supabase

def main():
    # Sprawdzamy klase 26 w tab_okres_final
    resp = supabase.table("tab_okres_final").select("id, samar_class_id, fuel_type_id, year_0, year_1").eq("samar_class_id", 26).execute()
    print("Klasa 26 w tab_okres_final:")
    print(json.dumps(resp.data, indent=2))
    
    # Sprawdzamy klase 26 w dawnej tabeli samar_class_depreciation_rates
    resp2 = supabase.table("samar_class_depreciation_rates").select("id, samar_class_id, fuel_type_id, year, base_depreciation_percent").eq("samar_class_id", 26).execute()
    print("\nKlasa 26 w samar_class_depreciation_rates:")
    print(json.dumps(resp2.data[:5], indent=2)) # pokazujemy pierwsze 5 rekordow
    
if __name__ == "__main__":
    main()
