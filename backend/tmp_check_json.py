import os
import sys
import asyncio
from dotenv import load_dotenv

sys.path.append('d:/kalk_v3/backend')
load_dotenv('d:/kalk_v3/backend/.env')

from core.database import supabase

def get_recent_jsons():
    res = supabase.table('vehicle_synthesis').select('brand, model, verification_status, synthesis_data').order('created_at', desc=True).limit(5).execute()
    for row in res.data:
        print(f"Vehicle: {row.get('brand')} {row.get('model')} (Status: {row.get('verification_status')})")
        dt = row.get('synthesis_data', {}).get('digital_twin', {})
        # Find all unqiue 'type' fields across pages
        types = set()
        pages = dt.get('pages', [])
        for page in pages:
            for item in page.get('content', []):
                if isinstance(item, dict):
                    types.add(item.get('type'))
                    if 'content' in item and isinstance(item['content'], list):
                        for sub in item['content']:
                            if isinstance(sub, dict):
                                types.add(sub.get('type'))
        print(f"  Found node types: {types}")
        
if __name__ == "__main__":
    get_recent_jsons()
