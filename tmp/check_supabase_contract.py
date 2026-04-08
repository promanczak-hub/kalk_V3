import sys
from pathlib import Path

# Add backend to sys.path
backend_dir = Path("backend").resolve()
sys.path.append(str(backend_dir))

try:
    from core.database import supabase
    from core.settings import SUPABASE_URL

    print(f"Connecting to {SUPABASE_URL}...")

    # Try to fetch one row from samar_class_base_rv to see columns
    response = supabase.table("samar_class_base_rv").select("*").limit(1).execute()
    print("\nTable: samar_class_base_rv")
    if response.data:
        print(f"Sample row keys: {list(response.data[0].keys())}")
    else:
        print("Table is empty or not found.")

    # Check other related tables
    for table in ["engines", "samar_classes", "depreciation_rates"]:
        res = supabase.table(table).select("*").limit(1).execute()
        if res.data:
            print(f"Table: {table} | Columns: {list(res.data[0].keys())}")
        else:
            print(f"Table: {table} | (Empty or no access)")

except Exception as e:
    print(f"Error: {e}")
