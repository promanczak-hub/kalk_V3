import os
import time
from supabase import create_client
from dotenv import load_dotenv

load_dotenv("../frontend/.env.local")


def monitor():
    url = os.environ.get("VITE_SUPABASE_URL")
    key = os.environ.get("VITE_SUPABASE_ANON_KEY")
    supabase = create_client(url, key)

    file_id = "91358867-4f0b-4233-b5ce-27d77658aab1"  # ID z pliku
    print(f"Monitoring ID: {file_id}")
    for _ in range(15):  # sprawdzamy przez ok. 30-40 sek
        res = (
            supabase.table("vehicle_synthesis")
            .select("verification_status, notes")
            .eq("id", file_id)
            .execute()
        )
        if res.data:
            status = res.data[0].get("verification_status")
            notes = res.data[0].get("notes")
            print(f"Status: {status} | Notes: {notes}")
            if status != "processing":
                break
        time.sleep(3)


if __name__ == "__main__":
    monitor()
