import asyncio
from core.database import supabase


async def main():
    res = (
        supabase.table("ltr_kalkulacje")
        .select("*")
        .eq("id", "f27d849a-61d3-4a70-86d6-2e836fe923ff")
        .execute()
    )
    data = res.data[0]

    stan = data.get("stan_json", {})
    print("Stan JSON:")
    # print keys and important values
    print(f"Brand: {stan.get('brand')}")
    print(f"Model: {stan.get('model')}")
    print(f"Toggles: {stan.get('toggles')}")
    print(f"Vehicle ID: {stan.get('vehicle_id')}")
    print(f"Base price: {stan.get('base_price_net')}")
    print(f"Equipment price: {stan.get('equipment_price_net')}")

    # Let's also check if it has calculations saved
    print("Calculations exist:", "calculations" in data)


if __name__ == "__main__":
    asyncio.run(main())
