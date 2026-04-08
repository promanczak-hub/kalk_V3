import sys
import os

# Add the current directory to sys.path (should be backend/)
sys.path.append(os.getcwd())

try:
    from core.database import supabase
    from core.settings import SUPABASE_URL, APP_ENV, SUPABASE_KEY

    print(f"--- Supabase Contract Diagnostic (ENV: {APP_ENV}) ---")
    print(f"URL: {SUPABASE_URL}")
    print(f"KEY: {'[SET]' if SUPABASE_KEY else '[MISSING]'}")

    # Check tables and their structures
    tables_to_check = [
        "samar_class_base_rv",
        "engines",
        "samar_classes",
        "depreciation_rates",
        "samar_class_service_rates",
        "replacement_car_rates",
    ]

    for table_name in tables_to_check:
        try:
            # We use select() and limit(1) to get the schema of one row
            res = supabase.table(table_name).select("*").limit(1).execute()
            print(f"\n[Table: {table_name}]")
            if res.data and len(res.data) > 0:
                print(f"  Columns: {list(res.data[0].keys())}")
                print(f"  Data Sample: {res.data[0]}")
            elif hasattr(res, "data") and len(res.data) == 0:
                print("  Status: Empty (but accessible)")
            else:
                print(f"  Status: No data or error. Raw: {res}")
        except Exception as e:
            print(f"  [!] Error checking table '{table_name}': {e}")

except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import backend modules: {e}")
    print(f"CWD: {os.getcwd()}")
    print(f"SYS.PATH: {sys.path}")
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
