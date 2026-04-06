import asyncio
from core.database import supabase


async def main():
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, brand, model, synthesis_data")
        .ilike("model", "%octavia%")
        .execute()
    )
    for v in res.data:
        vid = v["id"]
        sd = v.get("synthesis_data", {})
        version = sd.get("version", "")
        samar_id = sd.get("samar_id", "") or sd.get("configuration_code", "")

        c_res = (
            supabase.table("vehicle_matrix_cache")
            .select("monthly_price_net")
            .eq("vehicle_id", vid)
            .eq("margin_pct", 0)
            .eq("duration_months", 48)
            .eq("annual_mileage", 15000)
            .execute()
        )
        if c_res.data:
            val = float(c_res.data[0]["monthly_price_net"])
            disp = val / 0.86
            print(
                f"{version} (Samar: {samar_id}): 0-margin={val}, 14-margin UI={disp:.2f}"
            )


asyncio.run(main())
