import asyncio
from pprint import pprint

from backend.db.supabase import get_supabase
from backend.core.LTRKalkulator import LTRKalkulator


async def main():
    db = get_supabase()
    vehicle_id = "b8c1ee3c-5a94-45f2-bdf8-0f53e16ed780"
    res = db.table("vehicles").select("*").eq("id", vehicle_id).execute()
    if not res.data:
        print("Vehicle not found!")
        return

    vehicle = res.data[0]
    print(f"Vehicle: {vehicle.get('brand')} {vehicle.get('model')}")

    # Run calculator
    calc = LTRKalkulator(vehicle_id=vehicle_id)
    result = calc.calculate()

    print("\n--- TRACE ---")
    if "traces" in result and "utrata_wartosci" in result["traces"]:
        pprint(result["traces"]["utrata_wartosci"])
    else:
        print("No RV trace.")
        if hasattr(calc.utrata_wartosci_calc, "trace"):
            pprint(calc.utrata_wartosci_calc.trace)

    print("\n--- FULL RESULT ---")
    # pprint(result)


if __name__ == "__main__":
    asyncio.run(main())
