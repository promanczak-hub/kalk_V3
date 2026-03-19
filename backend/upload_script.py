import os
import sys
import uuid
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0"
    ".EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
)

if not url:
    print("Missing SUPABASE_URL")
    sys.exit(1)

sb = create_client(url, key)

file_path = r"C:\Users\proma\Downloads\KA1XST26262601C.pdf"
if not os.path.exists(file_path):
    print(f"File not found: {file_path}")
    sys.exit(1)

with open(file_path, "rb") as f:
    content = f.read()

filename = os.path.basename(file_path)
file_size = len(content)
mime_type = "application/pdf"
file_type = "pdf"

doc_id = str(uuid.uuid4())
brand = "Skoda"
model_family = "Karoq"
document_type = "price_list"
display_name = filename
storage_path = f"{brand}/{model_family}/{doc_id}.{file_type}"

print(f"Uploading to {storage_path}...")

res = sb.storage.from_("catalog-documents").upload(
    path=storage_path,
    file=content,
    file_options={"content-type": mime_type}
)

print(f"Upload to storage done: {res}")

row = {
    "id": doc_id,
    "brand": brand,
    "model_family": model_family,
    "document_type": document_type,
    "display_name": display_name,
    "version_tag": None,
    "is_active": True,
    "file_type": file_type,
    "storage_path": storage_path,
    "original_filename": filename,
    "file_size_bytes": file_size,
    "extraction_status": "pending",
    "variant_count": 0,
}

print(f"Inserting to model_document_sources...")

res2 = sb.table("model_document_sources").insert(row).execute()

print(f"Insert done: {res2.data[0]['id']}")
