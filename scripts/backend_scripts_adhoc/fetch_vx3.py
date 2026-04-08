import httpx

url = "https://gnpsdiarmwvqhqbyetce.supabase.co/rest/v1"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImducHNkaWFybXd2cWhxYnlldGNlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzE3NTU2MDEsImV4cCI6MjA4NzMzMTYwMX0.lBqpkkMGob1eODejdjaNksqlRkW5DSjh2A2yCQwcydQ"

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
}


def p():
    with httpx.Client() as client:
        # Check ltr_kalkulacje
        print("Sprawdzam pojazd w ltr_kalkulacje...")
        # Since PostgREST JSON path is supported: we can also just fetch all and filter locally, or use Supabase filter
        r = client.get(
            f"{url}/ltr_kalkulacje?select=id,numer_kalkulacji,stan_json,cena_netto&limit=50",
            headers=headers,
        )
        if r.status_code == 200:
            data = r.json()
            found = False
            for row in data:
                sj = row.get("stan_json", {})
                if sj and sj.get("vehicle_id") == "VX9RXG2R":
                    print("ZNALAZŁEM KALKULACJĘ!")
                    print(f"Numer: {row.get('numer_kalkulacji')}")
                    print(f"Cena Netto DB: {row.get('cena_netto')}")

                    okres = sj.get("okres_bazowy")
                    przebieg = sj.get("przebieg_bazowy")
                    base_price = sj.get("base_price_net")
                    print(f"Baza: {base_price}")
                    print(f"Opcje pricingu z json: {sj.get('pricing')}")
                    found = True
                    break

            if not found:
                print("Nie znalazlem VX9RXG2R w ubs. 50 kalkulacjach")
                # spróbujmy odszukać dokładnie ten ID, np numer KALK/2026/04/DCA5D2
                for row in data:
                    if row.get("numer_kalkulacji") == "KALK/2026/04/DCA5D2":
                        print("ZNALAZŁEM PO NUMERZE KALKULACJI z screena!")
                        print(row)
        else:
            print("Błąd:", r.text)


if __name__ == "__main__":
    p()
