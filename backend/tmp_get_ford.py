import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append('d:/kalk_v3/backend')
load_dotenv('d:/kalk_v3/backend/.env')
load_dotenv('d:/kalk_v3/frontend/.env.local')

from core.database import supabase

def get_last_ford():
    # Query vehicle_synthesis for the latest Ford
    res = supabase.table('vehicle_synthesis').select('*').ilike('brand', '%Ford%').order('created_at', desc=True).limit(1).execute()
    if res.data:
        ford = res.data[0]
        print(f"ID: {ford['id']}")
        print(f"Brand: {ford['brand']}")
        print(f"Model: {ford['model']}")
        print(f"Status: {ford['verification_status']}")
        print(f"Notes: {ford.get('notes')}")
        print(f"Created: {ford['created_at']}")
        
        # Write the synthesis_data to a file for checking
        import json
        with open('d:/kalk_v3/backend/tmp_ford_data.json', 'w', encoding='utf-8') as f:
            json.dump(ford, f, indent=2, ensure_ascii=False)
        print("Data dumped to tmp_ford_data.json")
    else:
         print("No Ford found in vehicle_synthesis")

if __name__ == "__main__":
    get_last_ford()
