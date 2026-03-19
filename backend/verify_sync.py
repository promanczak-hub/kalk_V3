import logging
from datetime import datetime, timezone
import requests
import json
from core.database import supabase

# Manual check of last_settings_update
def check_sync():
    print("--- 1. Checking Control Center last_settings_update ---")
    resp = supabase.table("control_center").select("last_settings_update").eq("id", 1).execute()
    if resp.data:
        print(f"Current last_settings_update: {resp.data[0]['last_settings_update']}")
    else:
        print("Control center record not found.")

    print("\n--- 2. Checking a sample cache entry's calculated_at ---")
    # Octavia vehicle ID from previous investigative sessions: 158e4de0-e3c9-488f-b224-676be5659a5d
    vid = "158e4de0-e3c9-488f-b224-676be5659a5d"
    resp = supabase.table("vehicle_matrix_cache").select("calculated_at").eq("vehicle_id", vid).limit(1).execute()
    if resp.data:
        print(f"Vehicle {vid} cache calculated_at: {resp.data[0]['calculated_at']}")
    else:
        print(f"No cache found for {vid}")

if __name__ == "__main__":
    check_sync()
