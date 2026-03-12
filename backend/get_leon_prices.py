import asyncio
from core.database import supabase


async def main():
    res = (
        supabase.table("vehicle_synthesis")
        .select("model, synthesis_data")
        .eq("id", "c81aac34-abeb-4dc7-884a-6c26488c099b")
        .execute()
    )
    data = res.data[0]

    synth = data["synthesis_data"]
    card = synth.get("card_summary", {})
    ai = synth.get("mapped_ai_data", {})

    base_price_str = card.get("base_price", "")
    equip_price_str = card.get("equipment_price", "0")
    total_price_str = card.get("total_price_discounted", card.get("total_price", "0"))

    print(f"Base price str: {base_price_str}")
    print(f"Equip price str: {equip_price_str}")
    print(f"Total price str: {total_price_str}")

    # We also need to check the exact payload the frontend sends in CalculatorPanel.tsx


if __name__ == "__main__":
    asyncio.run(main())
