import urllib.request
import json

url = "https://gnpsdiarmwvqhqbyetce.supabase.co/rest/v1/rpc/execute_sql"
headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc1NTYwMSwiZXhwIjoyMDg3MzMxNjAxfQ.rJv7Z1hHydLSrNRivDmBR_5S5zrQ6a7_6Jg6blUCoaU",
    "Content-Type": "application/json",
}
data = json.dumps({"query": "SELECT 1 as num"}).encode("utf-8")

req = urllib.request.Request(url, method="POST", headers=headers, data=data)
try:
    with urllib.request.urlopen(req) as resp:
        print("Success:", resp.read().decode())
except Exception as e:
    print("Failed:", e)
    if hasattr(e, "read"):
        print(e.read().decode())
