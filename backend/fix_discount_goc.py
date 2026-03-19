import json
import logging
import os
from dotenv import load_dotenv

# Load correct env file depending on run folder
if os.path.exists("../frontend/.env.local"):
    load_dotenv("../frontend/.env.local")
else:
    load_dotenv()

from core.database import supabase
from core.pipeline_discounts import match_fleet_discount

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_discount_for_octavia():
    offer_number = 'GOC-24-332599'
    print(f"Fetching vehicle with offer {offer_number}...")

    # Fetch vehicle
    # Using JSON operator to find the right synthesis_data
    response = supabase.table("vehicle_synthesis").select("id, synthesis_data").eq("external_id", offer_number).execute()
    
    if not response.data:
        # Fallback if external_id isn't it
        response = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
        matches = [row for row in response.data if row.get("synthesis_data", {}).get("digital_twin", {}).get("offer_number") == offer_number]
        if not matches:
            print("Could not find vehicle in DB.")
            return
        row = matches[0]
    else:
        row = response.data[0]

    veh_id = row['id']
    synthesis_data = row['synthesis_data']

    print(f"Running match_fleet_discount for vehicle ID: {veh_id}")
    updated_data = match_fleet_discount(synthesis_data)

    print("Updated card_summary:")
    print(json.dumps(updated_data.get('card_summary', {}), indent=2, ensure_ascii=False))

    print("Saving to DB...")
    update_res = supabase.table("vehicle_synthesis").update({"synthesis_data": updated_data}).eq("id", veh_id).execute()
    print("Update result:", update_res)

if __name__ == "__main__":
    fix_discount_for_octavia()

import sys
sys.path.insert(0, 'd:\\kalk_v3\\backend')
