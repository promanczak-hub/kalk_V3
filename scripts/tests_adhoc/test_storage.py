import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")

def test_storage():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    print(f"Testing storage with URL: {url}")
    supabase: Client = create_client(url, key)
    
    try:
        buckets = supabase.storage.list_buckets()
        print(f"Buckets: {buckets}")
        
        # Test download of a non-existent file to see if we can reach the bucket
        try:
            res = supabase.storage.from_("offers_excel").list()
            print(f"Files in bucket 'offers_excel': {res}")
        except Exception as e:
            print(f"Error listing files in 'offers_excel': {e}")

    except Exception as e:
        print(f"General Storage Error: {e}")

if __name__ == "__main__":
    test_storage()
