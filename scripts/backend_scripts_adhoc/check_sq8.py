import asyncio
from core.database import supabase
import pandas as pd


async def run():
    vids = [
        "9ea2310b-2de1-414f-9f2e-8b3934ccc116",
        "2577c0ed-edbd-4689-b97f-84192e3751b1",
        "957c026b-fe03-4b1f-aa2c-18dacc253fa9",
        "059d9963-c18a-45f4-8b4e-36bba4b9b34d",
        "a54e3f2b-f289-447a-9fc8-e8e268c70059",
    ]

    for vid in vids:
        print("\n\nChecking:", vid)
        # Check cache
        cache = (
            supabase.table("vehicle_matrix_cache")
            .select(
                "kalkulacja_id, duration_months, annual_mileage, monthly_price_net, calculated_at"
            )
            .eq("vehicle_id", vid)
            .execute()
        )
        if cache.data:
            df = pd.DataFrame(cache.data)
            print("Cache variants for", vid)
            print(df.groupby("kalkulacja_id").size())

            latest = df.sort_values("calculated_at", ascending=False).iloc[0][
                "kalkulacja_id"
            ]
            latest_rows = df[df["kalkulacja_id"] == latest]

            match = latest_rows[
                (latest_rows["duration_months"] == 60)
                & (latest_rows["annual_mileage"] == 20000)
            ]
            if len(match) > 0:
                print("60m/20k found in latest:", match.to_dict("records"))
            else:
                print("60m/20k NOT FOUND for the latest kalkulacja_id!")
                any_match = df[
                    (df["duration_months"] == 60) & (df["annual_mileage"] == 20000)
                ]
                if len(any_match) > 0:
                    print(
                        "BUT it was found in OTHER kalkulacja_id:",
                        any_match["kalkulacja_id"].unique(),
                    )
                    print("Times for these kalkulacja_ids:")
                    for kid in any_match["kalkulacja_id"].unique():
                        print(
                            kid,
                            df.loc[df["kalkulacja_id"] == kid, "calculated_at"].iloc[0],
                        )
                else:
                    print("AND NOT FOUND anywhere in cache!")

            print("ALL kalkulacja_id times:")
            for kid in df["kalkulacja_id"].unique():
                print(kid, df.loc[df["kalkulacja_id"] == kid, "calculated_at"].max())
        else:
            print("No cache data for", vid)


if __name__ == "__main__":
    asyncio.run(run())
