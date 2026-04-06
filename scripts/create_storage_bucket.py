import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

# Load dotenv from current directory
load_dotenv("backend/.env")

from core.database import supabase

def create_storage_bucket():
    try:
        bucket_id = "offers_excel"
        print(f"Creating storage bucket: {bucket_id}...")
        
        # Check if already exists first
        buckets = supabase.storage.list_buckets()
        if any(b.id == bucket_id for b in buckets):
            print(f"Bucket {bucket_id} already exists.")
            # Ensure it's public (most methods expect public access for shared offers)
            supabase.storage.update_bucket(bucket_id, {"public": True})
            print(f"Bucket {bucket_id} updated to public.")
        else:
            supabase.storage.create_bucket(bucket_id, options={"public": True})
            print(f"Bucket {bucket_id} created successfully (public: True).")
            
    except Exception as e:
        print("Error creating storage bucket:", str(e))

if __name__ == "__main__":
    create_storage_bucket()
