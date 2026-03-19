
import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.database import supabase
from core.matrix_cache_job import refresh_matrix_cache_for_vehicles, calculate_live_ltr_tile
from core.models import ControlCenterSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_parity(vehicle_id: str):
    print(f"\n=== VERIFYING PARITY FOR VEHICLE: {vehicle_id} ===")
    
    # 1. Refresh cache for this vehicle
    print("Refreshing cache...")
    refresh_matrix_cache_for_vehicles([vehicle_id])
    
    # 2. Fetch the cached results (specifically for margin_pct=0.0)
    print("Fetching cached results (margin 0.0)...")
    res = supabase.table("vehicle_matrix_cache").select("*").eq("vehicle_id", vehicle_id).eq("margin_pct", 0).execute()
    cached_rows = res.data or []
    
    if not cached_rows:
        print("ERROR: No cached results found!")
        return
        
    print(f"Found {len(cached_rows)} cached tiles.")
    
    # 3. Choose a few tiles to verify live
    test_params = [
        (36, 15000),
        (48, 20000),
        (24, 10000)
    ]
    
    all_match = True
    for dur, mileage in test_params:
        cached_row = next((r for r in cached_rows if r["duration_months"] == dur and r["annual_mileage"] == mileage), None)
        if not cached_row:
            print(f"Warning: No cached tile for {dur}m / {mileage}km")
            continue
            
        cached_price = float(cached_row["monthly_price_net"])
        
        # Calculate live
        live_price = calculate_live_ltr_tile(vehicle_id, dur, mileage)
        
        diff = abs(cached_price - live_price) if live_price is not None else 999999
        
        status = "MATCH ✅" if diff < 0.01 else f"MISMATCH ❌ (Diff: {diff})"
        if diff >= 0.01:
            all_match = False
            
        print(f"Tile {dur}m / {mileage}km: Cache={cached_price:.2f} | Live={live_price:.2f} | {status}")

    if all_match:
        print("\nSUCCESS: 100% Parity achieved for the checked tiles!")
    else:
        print("\nFAILURE: Price discrepancies detected.")

if __name__ == "__main__":
    # Test with SKODA Karoq (19" wheels)
    target_vid = "3ec82f6d-1b43-4967-b511-8bfd65266fcc"
    verify_parity(target_vid)
