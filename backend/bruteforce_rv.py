import asyncio
from core.samar_rv import RVInput, SamarRVCalculator
from core.database import supabase


async def test_combos():
    engine_id = 9  # diesel

    rv_input = RVInput(
        samar_class_id=4,  # D średnia
        engine_id=engine_id,
        brand_name="SKODA",
        model_name="Superb Combi",
        months=36,
        total_km=140000,
        capex_base_net=201504.07,
        capex_options_net=28211.38,  # using exact value from DB stan_json
        is_metalic=True,
        rocznik="current",
        manual_wr_correction=0.0,
    )

    res_cls = (
        supabase.table("samar_classes")
        .select("id")
        .ilike("name", "%D Średnia%")
        .execute()
    )
    if res_cls.data:
        rv_input.samar_class_id = res_cls.data[0]["id"]

    found = False
    for months in [24, 36, 48, 60, 72]:
        for total_km in range(10000, 200001, 10000):
            rv_input.months = months
            rv_input.total_km = total_km
            calc = SamarRVCalculator(rv_input)
            out = calc.calculate()
            if abs(out.wr_net - 86491.87) < 5:
                print(
                    f"FOUND MATCH: Months: {months:2d}, KM: {total_km:6d} -> RV Netto: {out.wr_net:.2f}"
                )
                found = True

    if not found:
        print("No match found for ~86491.87")


if __name__ == "__main__":
    asyncio.run(test_combos())
