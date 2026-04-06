import json
from core.database import supabase


def dump(code):
    res = supabase.table("vehicle_synthesis").select("synthesis_data").execute()
    for r in res.data:
        sd = r["synthesis_data"] or {}
        if code in str(sd):
            with open(f"d:/kalk_v3/backend/{code}.json", "w", encoding="utf-8") as f:
                json.dump(sd, f, indent=2, ensure_ascii=False)
            print(f"Dumped {code}")
            return


dump("CBGM55VH")
dump("CBQDKGWL")
