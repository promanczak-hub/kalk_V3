import urllib.request
import json


def fetch_all():
    db_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"

    url = f"{db_url}/rest/v1/fleet_management_view?select=*"  # Pobieramy wszystko

    req = urllib.request.Request(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Range-Unit": "items",
        },
    )

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        with open("d:/kalk_v3/backend/online_all.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Zapisano {len(data)} obiektów.")


if __name__ == "__main__":
    fetch_all()
