"""Quick polling helper — used by dump task to wait for extraction to finish."""
import sys
import time

sys.path.insert(0, "D:\\kalk_v3\\backend")
from core.database import supabase

vehicle_id = sys.argv[1] if len(sys.argv) > 1 else ""
max_wait = int(sys.argv[2]) if len(sys.argv) > 2 else 240
poll = int(sys.argv[3]) if len(sys.argv) > 3 else 10

last_status = None
deadline = time.time() + max_wait
while time.time() < deadline:
    res = (
        supabase.table("vehicle_synthesis")
        .select("verification_status, brand, model")
        .eq("id", vehicle_id)
        .single()
        .execute()
    )
    row = res.data or {}
    status = row.get("verification_status")
    if status != last_status:
        print(f"status={status!r} brand={row.get('brand')!r} model={row.get('model')!r}", flush=True)
        last_status = status
    if status in ("needs_review", "completed", "error"):
        print(f"FINAL {status}", flush=True)
        sys.exit(0)
    time.sleep(poll)

print(f"TIMEOUT last={last_status}", flush=True)
sys.exit(2)
