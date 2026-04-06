
# Używamy httpx dla pewności
import httpx

url = 'https://gnpsdiarmwvqhqbyetce.supabase.co/rest/v1'
key = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NTU2MDEsImV4cCI6MjA4NzMzMTYwMX0.lBqpkkMGob1eODejdjaNksqlRkW5DSjh2A2yCQwcydQ'

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

def check_db():
    print("Sprawdzam ID: VX9RXG2R...")
    with httpx.Client() as client:
        # Sprawdź samar_data
        r = client.get(f"{url}/samar_data?id=eq.VX9RXG2R", headers=headers)
        if r.status_code == 200 and r.json():
            print("SAMAR DATA:", r.json())
        
        # Sprawdź tabele vehicles jeśli istnieje
        r2 = client.get(f"{url}/vehicles?id=eq.VX9RXG2R", headers=headers)
        if r2.status_code == 200 and r2.json():
            print("VEHICLES:", r2.json())
            
        r3 = client.get(f"{url}/kalkulacje_historias?limit=5&order=created_at.desc", headers=headers)
        if r3.status_code == 200 and r3.json():
            for k in r3.json():
                print("KALK:", k.get("numer_kalkulacji"), k.get("wynik_rata_netto"))

if __name__ == "__main__":
    check_db()
