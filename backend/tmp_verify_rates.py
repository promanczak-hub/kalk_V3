from core.database import supabase

resp = (
    supabase.table("replacement_car_rates")
    .select("samar_class_id, samar_class_name, daily_rate_net, average_days_per_year")
    .order("samar_class_id")
    .execute()
)

for r in resp.data:
    cid = r["samar_class_id"]
    name = r["samar_class_name"]
    rate = r["daily_rate_net"]
    days = r["average_days_per_year"]
    yearly = rate * days
    print(f"  {cid:>3}  {name:<45}  {rate:>7.0f} zl/doba  |  {yearly:>8.1f} zl/rok")

print(f"\nTotal: {len(resp.data)} rows")
