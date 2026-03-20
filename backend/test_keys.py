from supabase import create_client

url = "https://gnpsdiarmwvqhqbyetce.supabase.co"
keys = [
    "sb_publishable_hXJmqJJyfONRRHwSUQjNVA_9w2k3TF9",
    "sbp_aaa03eb39fadec3d0b69ac0590ff7440d104e8a9",
    "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz",
]

for key in keys:
    print(f"\nTesting key starting with: {key[:15]}...")
    try:
        sb = create_client(url, key)
        # Try a simple select that should work for anon or service_role if RLS allows
        res = (
            sb.table("samar_classes").select("count", count="exact").limit(1).execute()
        )
        print(f"SUCCESS! Key works. Count: {res.count}")
    except Exception as e:
        print(f"FAILED: {e}")
