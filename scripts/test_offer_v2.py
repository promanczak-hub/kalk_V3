import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from core.offer_generator import ExcelOfferGenerator
from core.database import supabase


def test_manual_enrichment():
    # Use the real IDs we found during research
    calc_id = "4211d760-0b6b-45e0-aa6e-df179a09d68a"
    vehicle_id = "e017f6d2-3162-4f2d-8a1e-62f674e4f439"

    print(f"Testing enrichment for calc_id: {calc_id}")

    # Mock item
    item = {
        "brand": "Toyota",
        "model": "Proace Max",
        "powertrain": "2.2 Diesel 180 KM A/T",
        "term": 24,
        "mileage": 20000,
        "net_installment": 4278.0,
        "calculation_data": {"kalkulacja_id": calc_id, "vehicle_id": vehicle_id},
    }

    # Manual enrichment logic (from route)
    matrix_res = (
        supabase.table("vehicle_matrix_cache")
        .select("*")
        .eq("kalkulacja_id", calc_id)
        .execute()
    )
    if matrix_res.data:
        item["matrix_data"] = matrix_res.data
        print(f"Found {len(matrix_res.data)} matrix entries.")

    synth_res = (
        supabase.table("vehicle_synthesis")
        .select("synthesis_data")
        .eq("id", vehicle_id)
        .execute()
    )
    if synth_res.data:
        synth = synth_res.data[0].get("synthesis_data", {})
        item["standard_equipment"] = synth.get("digital_twin", [])
        item["factory_options"] = [
            opt
            for opt in synth.get("digital_twin", [])
            if "Pakiet" in opt or "lakier" in opt.lower()
        ]
        print(
            f"Found {len(item['standard_equipment'])} standard options and {len(item['factory_options'])} derived factory options."
        )

    # Generation
    generator = ExcelOfferGenerator(
        template_path="core/templates/template_oferta_v2.xlsx"
    )
    excel_bytes = generator.generate_offer(
        client_name="Testowy Klient Sp. z o.o.", client_nip="1234567890", items=[item]
    )

    output_path = "test_premium_offer.xlsx"
    with open(output_path, "wb") as f:
        f.write(excel_bytes)

    print(f"Successfully generated test offer: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    try:
        test_manual_enrichment()
    except Exception:
        import traceback

        traceback.print_exc()
