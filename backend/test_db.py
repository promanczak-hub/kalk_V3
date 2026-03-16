import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
load_dotenv("../frontend/.env.local")

SUPABASE_URL = os.environ.get("VITE_SUPABASE_URL")
SUPABASE_KEY = os.environ.get("VITE_SUPABASE_ANON_KEY")
if not SUPABASE_KEY:
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

payload = {
    "id": "11111111-1111-1111-1111-111111111111",
    "brand": "CUPRA",
    "model_family": "Leon",
    "document_type": "OTHER",
    "display_name": "test_leon.pdf",
    "is_active": True,
    "file_type": "pdf",
    "storage_path": "test",
    "original_filename": "test.pdf",
    "file_size_bytes": 100,
    "extraction_status": "extracting",
    "variant_count": 0,
}

try:
    print("Testing insert...")
    response = supabase.schema("reverse_search").table("model_document_sources").insert(payload).execute()
    print("Success:", response)
    # Clean up
    supabase.schema("reverse_search").table("model_document_sources").delete().eq("id", "11111111-1111-1111-1111-111111111111").execute()
except Exception as e:
    print("Error:", e)
