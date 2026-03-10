import urllib.request
import json

url = "https://gnpsdiarmwvqhqbyetce.supabase.co/rest/v1/oferty_pojazdy?vin=in.(WBA11GR0309349983,WBA11GR0609352697)"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU"

req = urllib.request.Request(url)
req.add_header("apikey", token)
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/json")

try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))
        with open("d:/kalk_v3/backend/online_x3_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Pobrano {len(data)} rekordów.")
        for d in data:
            print(
                f"- VIN: {d.get('vin')} | klasa: {d.get('samar_klasa')} | ID: {d.get('samar_id')}"
            )
except Exception as e:
    print(f"Error: {e}")
