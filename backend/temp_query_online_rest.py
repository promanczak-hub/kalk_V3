import urllib.request
import json
from urllib.error import HTTPError


def fetch_bmw_x3_rest():
    db_url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"

    # Korygujemy field z `json_data` na `synthesis_data` wg ustaleń z kodu frontendowego
    url = f"{db_url}/rest/v1/fleet_management_view?or=(synthesis_data->>vin.eq.WBA11GR0309349983,synthesis_data->>vin.eq.WBA11GR0609352697)"

    req = urllib.request.Request(
        url,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Range-Unit": "items",
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            with open(
                "d:/kalk_v3/backend/online_bmw_x3_rest.json", "w", encoding="utf-8"
            ) as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(
                f"Zapisano {len(data)} pojazdów poprzez REST do online_bmw_x3_rest.json"
            )
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")


if __name__ == "__main__":
    fetch_bmw_x3_rest()
