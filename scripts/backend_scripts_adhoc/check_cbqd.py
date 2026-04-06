import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from core.database import supabase

def main():
    print("Fetching CBQDKGWL from DB...")
    try:
        vid = None
        res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
        for r in res.data:
            if "CBQDKGWL" in str(r.get("synthesis_data", "")):
                vid = r["id"]
                break
        
        if not vid:
            print("Vehicle not found!")
            return
        
        print(f"Found CBQDKGWL at UUID: {vid[:8]}...")
        matrix = supabase.table("vehicle_matrix_cache").select("*").eq("vehicle_id", vid).eq("duration_months", 36).eq("annual_mileage", 50000).execute()
        if matrix.data:
            print(f"\nMatrix Cache (36m, 50k/y):")
            for m in matrix.data:
                print(f"- Kalk ID: {m['kalkulacja_id']}, Monthly Net: {m['monthly_price_net']}, Margin: {m['margin_pct']}, Discount: {m['discount_pct']}")
        else:
            print("\nNo matrix cache for 36m, 50k!")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("EXCEPTION: ", repr(e))

if __name__ == "__main__":
    main()
