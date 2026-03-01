import os
import uuid
import hashlib
import requests
import time
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def test_api():
    # 1. Setup Supabase
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    file_path = r"C:\Users\proma\Downloads\BMW 320i Touring rok produkcji 2025.pdf"

    with open(file_path, "rb") as f:
        file_bytes = f.read()
        md5_hash = hashlib.md5(file_bytes).hexdigest()

    # delete old duplicate mock runs
    supabase.table("vehicle_synthesis").delete().eq("file_hash", md5_hash).execute()

    file_id = str(uuid.uuid4())
    print(f"Creating row for File ID: {file_id}")
    supabase.table("vehicle_synthesis").insert(
        {"id": file_id, "verification_status": "processing", "file_hash": md5_hash}
    ).execute()

    print("Sending POST request to localhost:8000/api/extract/async")
    with open(file_path, "rb") as f:
        files = {"file": ("BMW 320i Touring.pdf", f, "application/pdf")}
        data = {"file_id": file_id}
        response = requests.post(
            "http://localhost:8000/api/extract/async", files=files, data=data
        )

    print(f"API Returned: {response.text}")
    print("Waiting 45s for Background Task to complete...")
    for _ in range(15):
        time.sleep(3)
        res = (
            supabase.table("vehicle_synthesis")
            .select("verification_status, notes")
            .eq("id", file_id)
            .execute()
        )
        status = res.data[0].get("verification_status") if res.data else "Missing"
        if status != "processing":
            print(f"DONE! Status is now: {status}. Notes: {res.data[0].get('notes')}")
            break


if __name__ == "__main__":
    test_api()
