import os
from supabase import create_client
from dotenv import load_dotenv

# Load env from .env in the same dir
load_dotenv(".env")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print(f"Missing Supabase credentials. URL: {url}, Key set: {bool(key)}")
    exit(1)

supabase = create_client(url, key)

buckets = ["catalog-documents", "vehicles", "offers_excel"]

for bucket in buckets:
    print(f"\nListing Files in Bucket: {bucket}")
    try:
        res = supabase.storage.from_(bucket).list(options={"limit": 100})
        if not res:
            print(" - (empty)")
            continue
        for item in res:
            name = item.get("name")
            if item.get("id") is None:  # It's a folder
                print(f" [DIR] {name}")
                # Optional: recursive list if needed
                continue
            metadata = item.get("metadata", {})
            mimetype = metadata.get("mimetype", "unknown")
            print(f" - {name} ({mimetype})")
    except Exception as e:
        print(f"Error listing {bucket}: {e}")
