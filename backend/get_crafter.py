import asyncio
from core.database import supabase
from core.LTRSubCalculatorSerwisNew import ServiceCalculator, ServiceCalculatorInput


async def main():
    res = (
        supabase.table("vehicle_synthesis")
        .select("id, model, synthesis_data")
        .ilike("model", "%Crafter Furgon%")
        .limit(1)
        .execute()
    )
    data = res.data[0]

    synth = data["synthesis_data"]
    mapped = synth.get("mapped_ai_data", {})
    samar_class = mapped.get("samar_category", "")
    engine_class = mapped.get("engine_class", "")

    # We need the ID for samar and engine
    # Let's get them from DB
    res_samar = (
        supabase.table("samar_classes").select("id").eq("name", samar_class).execute()
    )
    samar_class_id = res_samar.data[0]["id"] if res_samar.data else 0
    res_engine = (
        supabase.table("engines").select("id").eq("category", engine_class).execute()
    )
    engine_type_id = res_engine.data[0]["id"] if res_engine.data else 0

    power_hp = synth.get("card_summary", {}).get("power_hp", 130)
    power_kw = power_hp * 0.735499

    print(f"Model: {data['model']}")
    print(f"Class: {samar_class} (ID: {samar_class_id})")
    print(f"Engine: {engine_class} (ID: {engine_type_id})")
    print(f"Power: {power_kw:.1f} kW")

    sc_input = ServiceCalculatorInput(
        z_serwisem=True,
        opcja_serwisowa="ASO",
        normatywny_przebieg_mc=1667,
        samar_class_id=samar_class_id,
        engine_type_id=engine_type_id,
        power_kw=power_kw,
        przebieg=160000,
        okres=48,
        pakiet_serwisowy=0.0,
        inne_koszty_serwisowania_netto=0.0,
    )

    calc = ServiceCalculator(sc_input)
    # Wywołujemy prywatne metody żeby zobaczyć stawki
    band = calc._determine_power_band()
    calc._fetch_rate_from_db()

    print(f"Power band: {band}")
    print(f"Rate per km: {calc._rate_per_km}")

    result = calc.calculate()
    print(f"Monthly Cost: {result}")


if __name__ == "__main__":
    asyncio.run(main())
