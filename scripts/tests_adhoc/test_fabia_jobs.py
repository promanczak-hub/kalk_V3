import json
from core.database import supabase


def main():
    res = supabase.table("vehicle_synthesis").select("id, synthesis_data").execute()
    fabias = []
    for v in res.data:
        sd_str = json.dumps(v.get("synthesis_data", {}))
        if "Skoda" in sd_str and "Fabia" in sd_str:
            fabias.append(v["id"])

    print(f"Fabias found: {len(fabias)}")
    for fid in fabias:
        jobs = (
            supabase.table("calculation_jobs")
            .select("*")
            .eq("vehicle_id", fid)
            .execute()
        )
        print(f"--- Jobs for {fid} ---")
        if not jobs.data:
            print("  NO JOBS FOUND")
        for j in jobs.data:
            print(
                f"  ID: {j['id']} | Status: {j['status']} | Error: {j.get('error_code')} - {j.get('error_detail')}"
            )


if __name__ == "__main__":
    main()
