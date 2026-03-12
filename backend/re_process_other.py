import os
import requests
from supabase import create_client
from dotenv import load_dotenv
import time

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def run():
    print("Szukam dokumentów OTHER dzisiejszych (np. Crafter)...")
    # Fetch OTHER docs
    resp = (
        supabase.table("document_library")
        .select("*")
        .eq("document_type", "OTHER")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    docs = resp.data or []

    crafter_docs = [d for d in docs if "Crafter" in d["file_name"]]
    print(
        f"Znaleziono {len(crafter_docs)} dokumentów Crafter sklasyfikowanych jako OTHER."
    )

    for doc in crafter_docs:
        print(f"--- Przetwarzanie: {doc['file_name']} ---")
        url = doc["document_url"]

        print("Pobieranie PDF...")
        res_pdf = requests.get(url)
        if res_pdf.status_code != 200:
            print(f"Błąd pobierania: {res_pdf.status_code}")
            continue

        file_bytes = res_pdf.content

        # We need to send it to /api/extract/async
        # But wait, we also need to create a row in vehicle_synthesis with a file_id to avoid the frontend duplicate check?
        # Let's just use the API, it handles file_id generation if not provided?
        # Actually /api/extract/async expects 'file_id' in form data.
        import uuid

        file_id = str(uuid.uuid4())

        # Prepare form data
        files = {"file": (doc["file_name"], file_bytes, "application/pdf")}
        data = {"file_id": file_id}

        print(f"Rejestracja w vehicle_synthesis: {file_id}")
        supabase.table("vehicle_synthesis").insert(
            {
                "id": file_id,
                "verification_status": "processing",
            }
        ).execute()

        print("Wysyłanie do /api/extract/async...")
        api_res = requests.post(
            "http://127.0.0.1:8000/api/extract/async", files=files, data=data
        )
        if api_res.status_code in [200, 202]:
            print("Zlecono pomyślnie. Usuwam z document_library...")
            supabase.table("document_library").delete().eq("id", doc["id"]).execute()
        else:
            print(f"Błąd wysyłania do API: {api_res.status_code} - {api_res.text}")

        time.sleep(1)


if __name__ == "__main__":
    run()
