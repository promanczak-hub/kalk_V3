import urllib.request
import json
from urllib.error import HTTPError


def fetch_all_rest():
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

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            # Filtr w pythonie
            filtered = [
                d
                for d in data
                if (
                    d.get("synthesis_data")
                    and isinstance(d["synthesis_data"], dict)
                    and d["synthesis_data"].get("make", "").upper() == "BMW"
                    and "X3" in d["synthesis_data"].get("model", "").upper()
                )
                or (
                    d.get("synthesis_data")
                    and isinstance(d["synthesis_data"], dict)
                    and d["synthesis_data"].get("vin")
                    in ("WBA11GR0309349983", "WBA11GR0609352697")
                )
            ]

            with open(
                "d:/kalk_v3/backend/online_bmw_x3_rest.json", "w", encoding="utf-8"
            ) as f:
                json.dump(filtered, f, indent=2, ensure_ascii=False)
            print(
                f"Pobrano {len(data)} z bazy, z czego po przefiltrowaniu X3 zapisano {len(filtered)} pojazdów do online_bmw_x3_rest.json"
            )
    except HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.read().decode()}")


if __name__ == "__main__":
    fetch_all_rest()
