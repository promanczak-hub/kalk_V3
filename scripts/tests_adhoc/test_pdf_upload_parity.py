import os
import asyncio
import httpx
from api.schemas.calculator import CalculatorInput
from core.database import supabase


async def main():
    filepath = r"C:\Users\proma\Downloads\car-card-CFX898YD.pdf"
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    print("--- 1. UPLOADING PDF ---")
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(filepath, "rb") as f:
            files = {"file": ("car-card-CFX898YD.pdf", f, "application/pdf")}
            data = {"file_id": "test-file-id-123"}
            r = await client.post(
                "http://localhost:8000/api/extract/async", data=data, files=files
            )
            if r.status_code != 200:
                print(f"Upload failed: {r.text}")
                return
            data = r.json()
            task_id = data.get(
                "file_id"
            )  # Note: endpoint returns {"status": "processing", "file_id": file_id}
            print("Zwrócono doc ID:", task_id)

    # Now we need to wait for vehicle synthesis to be ready, since there is no /status endpoint for extract/async!
    # Or maybe the celery task updates something.
    print("Wgrywanie rozpoczęte. Czekamy na ekstrakt w bazie...")

    vehicle_id = None
    for _ in range(60):  # 120s
        # Znajdź po file_id (niestety nie mamy auth, może znajdziemy najnowszy wiersz)
        resp = (
            supabase.table("vehicle_synthesis")
            .select("id, verification_status")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            latest = resp.data[0]
            if (
                latest.get("verification_status") == "human_verification_required"
                or latest.get("verification_status") == "verified"
            ):
                vehicle_id = latest.get("id")
                break
        await asyncio.sleep(2)

    if not vehicle_id:
        print("Nie otrzymano vehicle_id po zakonczeniu zadania.")
        return

    print(f"Otrzymano vehicle_id: {vehicle_id}")

    print("--- 3. SYMULACJA ZAPISU W VERTEX Z RABATEM 20% ---")
    # Pobieramy stan z bazy
    v_resp = (
        supabase.table("vehicles").select("stan_json").eq("id", vehicle_id).execute()
    )
    stan_json = v_resp.data[0].get("stan_json", {})

    # Aktualizujemy discount_pct
    stan_json["discount_pct"] = 0.20

    # Wywołujemy odświeżenie cache (dokładnie jak robi to UI VehicleActionButtons.tsx)
    payload = {"vehicle_id": vehicle_id, "stan_json": stan_json}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "http://localhost:8000/api/kalkulacje/matrix-cache/refresh", json=payload
        )
        if r.status_code != 200:
            print(f"Refresh failed: {r.text}")
            return

    print(
        "Refresh triggered, waiting for celery tasks to complete matrix generation..."
    )
    # Polling the celery job to finish, simplest way is to fetch cache until we see rows
    for _ in range(30):
        cache_resp = (
            supabase.table("vehicle_matrix_cache")
            .select("id")
            .eq("vehicle_id", vehicle_id)
            .execute()
        )
        if len(cache_resp.data) >= 116:  # Pelnę pokrycie matrixa
            break
        await asyncio.sleep(2)

    # Wait extra 2 sec just to be sure
    await asyncio.sleep(2)

    print(
        "--- 4. POBIERANIE WYNIKOW REVERSE SEARCH VS LIVE (48 mc, 25k km rocznie = 100k km całkowitego) ---"
    )

    frontend_margin = 0.15  # Założona marża do porównania
    DURATION = 48
    MILEAGE_CAP = 100000

    print(
        f"Użyte parametry: Marża: {frontend_margin * 100}%, Okres: {DURATION} mc, Przebieg cały: {MILEAGE_CAP} km"
    )

    # --- Live z Vertex Extractor ---
    req_payload = {
        "duration": DURATION,
        "total_mileage": MILEAGE_CAP,
        "pricing_margin_pct": frontend_margin
        * 100,  # CalculatorInput expects percentage (e.g. 15.0) -> wait, CalculatorInput usually expects float (e.g. 0.15). Let's check config.
        # Czekaj, w kodzie pricing_margin_pct domyślnie jest mnożone.
    }

    # Check what CalculatorInput expects for margin (0.15 vs 15)
    # W rpc_reverse_search przyjmuje np 0.15.
    calc_input_live = CalculatorInput(
        vehicle_id=vehicle_id,
        stan_json=stan_json,
        duration=DURATION,
        mileage_cap=MILEAGE_CAP,
        pricing_margin_pct=frontend_margin,  # 0.15
    )

    try:
        from core.LTRKalkulator import LTRKalkulator

        calculator = LTRKalkulator(calc_input_live)
        live_result = calculator.calculate()
        live_price = live_result["Cena_dla_klienta_netto"]
        live_base = live_result["Suma_Kalkulacji"]
    except Exception as e:
        print(f"Live calc failed: {e}")
        return

    # --- Reverse Search Cache Result ---
    # Symulujemy rpc_reverse_search
    query = (
        supabase.table("vehicle_matrix_cache")
        .select("*")
        .eq("vehicle_id", vehicle_id)
        .eq("duration", DURATION)
        .eq("mileage_cap", MILEAGE_CAP)
        .eq("margin_pct", 0)
        .order("monthly_price_net", desc=False)
        .limit(1)
        .execute()
    )

    if not query.data:
        print("Nie znaleziono w cache!")
        return

    row = query.data[0]
    cache_base_price = float(row["monthly_price_net"])
    # rpc_reverse_search robi w sql: monthly_price_net * (1 + margin_input)
    cache_final_price = cache_base_price * (1 + frontend_margin)

    print("\n" + "=" * 50)
    print("--- VERTEX EXTRACTOR (Wynik LIVE) ---")
    print(f"Kwota w UI (stan na 0% marży): {live_base:.2f} PLN")
    print(f"Wyliczona Opcja z 15% marży: {live_price:.2f} PLN")

    print("\n--- REVERSE SEARCH (Odczyt Cache ze zmienną Marżą Frontendową) ---")
    print(f"Cena bezpośrednio z bazy cache (dla 0%): {cache_base_price:.2f} PLN")
    print(
        f"Cena front Reverse Search z {frontend_margin * 100}% narzutem: {cache_final_price:.2f} PLN"
    )
    print("=" * 50)

    diff = abs(live_price - cache_final_price)
    print(f"Różnica PLN = {diff:.2f} PLN")
    if diff < 0.05:
        print("✅ PARITY ZGODNA (RABAT 20% ZACHOWANY W CACHEMATRIXI!)")
    else:
        print("❌ PARITY NIEZGODNA")


if __name__ == "__main__":
    asyncio.run(main())
