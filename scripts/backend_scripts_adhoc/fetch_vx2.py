import httpx

url = "https://gnpsdiarmwvqhqbyetce.supabase.co/rest/v1"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NTU2MDEsImV4cCI6MjA4NzMzMTYwMX0.lBqpkkMGob1eODejdjaNksqlRkW5DSjh2A2yCQwcydQ"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}

print("Pinging db...")
with httpx.Client() as client:
    r = client.get(f"{url}/samar_data?id=eq.VX9RXG2R", headers=headers)
    print("SAMAR:", r.status_code, r.text)

    r2 = client.get(f"{url}/samar_data?limit=1", headers=headers)
    if r2.status_code == 200:
        data = r2.json()
        if data:
            # Let's see what columns are there
            print("SAMAR COLUMNS:", list(data[0].keys()))

    # Maybe check kalkulacje histories for anything with 183569
    r3 = client.get(
        f"{url}/kalkulacje_historias?wynik_rata_netto=eq.183569", headers=headers
    )
    print("KALKULACJE 183569:", r3.status_code, r3.text)

    # Let's search samar_data for a price like 183569
    r4 = client.get(f"{url}/samar_data?cena_netto=eq.183569", headers=headers)
    print("SAMAR CENA NETTO 183569:", r4.status_code, r4.text)
