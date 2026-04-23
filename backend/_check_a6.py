from core.database import supabase

VID = "1b37728f-1bdd-4f9c-b696-21da38fe00ed"
vmc = supabase.table("vehicle_matrix_cache").select("vehicle_id, duration_months, annual_mileage, monthly_price_net").eq("vehicle_id", VID).limit(5).execute()
print(f"Rows in vehicle_matrix_cache: {len(vmc.data or [])}")
for r in vmc.data or []:
    print(f"  {r['duration_months']}mc, {r['annual_mileage']}km/r, {r['monthly_price_net']} PLN")

# Check calculation_jobs too
try:
    jobs = supabase.table("calculation_jobs").select("*").eq("vehicle_id", VID).execute()
    print(f"\ncalculation_jobs rows: {len(jobs.data or [])}")
    for j in jobs.data or []:
        print(f"  status={j.get('status')}, error={j.get('error_code')}")
except Exception as e:
    print(f"jobs error: {e}")

# Check celery
import subprocess
result = subprocess.run(["wmic", "process", "where", "name='python.exe'", "get", "commandline"], capture_output=True, text=True)
celery_lines = [l for l in result.stdout.splitlines() if "celery" in l.lower()]
print(f"\nCelery processes: {len(celery_lines)}")
for l in celery_lines:
    print(f"  {l.strip()}")
