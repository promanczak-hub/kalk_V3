import asyncio
from core.samar_rv import RVInput, SamarRVCalculator, get_samar_class_id
from pprint import pprint


async def run_test():
    # Dane dla Skody Superb Combi L&K
    # samar_category = "Podstawowa - D ŚREDNIA"
    samar_class_id = get_samar_class_id("Podstawowa - D ŚREDNIA")
    engine_id = 9  # Diesel (według DB, zazwyczaj 9 = Diesel (ON))
    # TODO: upewnić się, że Diesel to 9, sprawdzę

    # Przebieg i czas
    # Assuming from the screenshot/params standard 48 months 140000 km, or check user intent
    months = 48
    total_km = 140000

    # if total_km is different, I will need to know.
    # Usually standard quote is 48m, but 140k? Wait, if 48m, max 140k?
    # Or maybe 36m? Let's check typical calculation.

    rv_input = RVInput(
        samar_class_id=samar_class_id or 1,
        engine_id=engine_id,
        brand_name="SKODA",
        model_name="Superb Combi",
        months=months,
        total_km=total_km,
        capex_base_net=201504.07,
        capex_options_net=28211.38,
        paint_type_id=1,  # metalic placeholder, we just use is_metalic=True usually
        is_metalic=True,
        body_type_id=None,
        rocznik="current",
        zabudowa_apr_wr=False,
        zabudowa_type_id=None,
        manual_wr_correction=0.0,
    )

    try:
        from core.database import supabase

        res = (
            supabase.table("fuel_types").select("*").ilike("name", "%diesel%").execute()
        )
        if res.data:
            rv_input.engine_id = res.data[0]["id"]
            print(f"Using engine_id: {rv_input.engine_id} for Diesel")
    except:
        pass

    calc = SamarRVCalculator(rv_input)
    res = calc.calculate()
    pprint(res.debug)
    print(f"Final RV Netto: {res.wr_net}")


if __name__ == "__main__":
    asyncio.run(run_test())
