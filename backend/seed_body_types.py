"""Seed body_types table with standard vehicle body types."""

import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL", "http://127.0.0.1:54321")
key = os.environ.get(
    "SUPABASE_SERVICE_ROLE_KEY", "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz"
)
sb = create_client(url, key)

BODY_TYPES = [
    ("Hatchback", "Osobowy"),
    ("Kombi", "Osobowy"),
    ("Sedan", "Osobowy"),
    ("SUV", "Osobowy"),
    ("Liftback", "Osobowy"),
    ("Coupe", "Osobowy"),
    ("Cabrio", "Osobowy"),
    ("Minivan", "Osobowy"),
    ("5 drzwiowy", "Osobowy"),
    ("4 drzwiowy", "Osobowy"),
    ("Furgon", "Dostawczy"),
    ("Pickup", "Dostawczy"),
    ("Van", "Dostawczy"),
    ("Podwozie", "Dostawczy"),
    ("Wieloosobowy", "Dostawczy"),
    ("Dwuosobowy", "Dostawczy"),
    ("5 drzwiowy VAN", "Dostawczy"),
]

rows = [{"name": n, "vehicle_class": vc} for n, vc in BODY_TYPES]
resp = sb.table("body_types").upsert(rows, on_conflict="name").execute()
print(f"Inserted {len(resp.data)} body types OK")
for r in resp.data:
    print(f"  {r['vehicle_class']:12s} | {r['name']}")
