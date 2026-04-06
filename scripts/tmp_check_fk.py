import httpx

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
HEADERS = {"apikey": API_KEY, "Authorization": f"Bearer {SERVICE_KEY}"}
BASE = "http://127.0.0.1:54321/rest/v1"

tables_to_check = [
    "samar_class_depreciation_rates",
    "samar_class_mileage_corrections",
    "samar_rv_body_corrections",
    "replacement_car_rates",
    "insurance_rates",
    "damage_coefficients",
]

print("=== Checking FK references to Pciez (samar_class_id=30) ===")
for table in tables_to_check:
    try:
        r = httpx.get(
            f"{BASE}/{table}?samar_class_id=eq.30&select=id",
            headers=HEADERS,
        )
        data = r.json()
        count = len(data) if isinstance(data, list) else 0
        status = "HAS REFERENCES" if count > 0 else "Clean"
        print(f"  {table}: {count} rows  {status}")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")

print("\nDone.")
